//! Direct TFHE-rs integer-division control, not an implementation of recent papers.
use std::env;
use std::hint::black_box;
use std::time::Instant;
use tfhe::integer::{gen_keys_radix, RadixCiphertext};
use tfhe::shortint::parameters::PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS;
use tfhe::{get_pbs_count, reset_pbs_count};

fn cases(t:u64)->Vec<(u64,u64)> {
    let mut result=vec![(0,t-1),(1,1),(t-1,1),(t-1,t-1),(t/2-2,t-3),
        (t-2,3),(t/2-1,2),(t/2,3),(t-3,4),(t/2+1,t/2)];
    for m in 0..t {for d in 1..t {if !result.contains(&(m,d)){result.push((m,d));}}}
    result
}

fn main(){
    let t:u64=env::args().nth(1).unwrap_or("16".into()).parse().unwrap();
    assert!([16,32,64].contains(&t));
    let blocks=if t==16 {2} else {3};
    let (cks,mut sks)=gen_keys_radix(PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,blocks);
    sks.set_deterministic_pbs_execution(false);
    println!("BASELINE_ENV,tfhe_rs=0.8.7,t={t},radix_blocks={blocks},parameter=PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,repetitions=30,warmups=0,operation=div_parallelized");
    let mut times=Vec::new();
    let mut counts=Vec::new();
    for (i,(m,d)) in cases(t).into_iter().take(30).enumerate(){
        let cm:RadixCiphertext=cks.encrypt(m);
        let cd:RadixCiphertext=cks.encrypt(d);
        reset_pbs_count();
        let start=Instant::now();
        let cq=black_box(sks.div_parallelized(&cm,&cd));
        let ms=start.elapsed().as_secs_f64()*1000.0;
        let pbs=get_pbs_count();
        let actual:u64=cks.decrypt(&cq);
        assert_eq!(actual,m/d);
        println!("BASELINE_RESULT,t={t},index={i},m={m},d={d},actual={actual},pbs_count={pbs},elapsed_ms={ms:.6}");
        times.push(ms);counts.push(pbs);
    }
    println!("BASELINE_SUMMARY,PASS,t={t},cases=30,average_ms={:.6},average_pbs={:.3}",
       times.iter().sum::<f64>()/30.0,counts.iter().sum::<u64>() as f64/30.0);
}
