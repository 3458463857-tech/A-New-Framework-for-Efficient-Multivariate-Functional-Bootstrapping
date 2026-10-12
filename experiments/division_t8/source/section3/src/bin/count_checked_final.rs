//! Independent encrypted bits -> checked sum -> one threshold/interval PBS.
use std::{env,fs,hint::black_box,time::Instant};
use tfhe::shortint::{gen_keys,parameters::PARAM_MESSAGE_2_CARRY_4_KS_PBS};
use tfhe::{get_pbs_count,reset_pbs_count};
fn main(){
    let n:usize=env::args().nth(1).expect("n required").parse().unwrap();
    let predicate=env::args().nth(2).expect("threshold or interval required");
    let path=env::args().nth(3).expect("input manifest required");
    assert!([12,16].contains(&n));assert!(["threshold","interval"].contains(&predicate.as_str()));
    let text=fs::read_to_string(&path).unwrap();let mut lines=text.lines();
    assert_eq!(lines.next(),Some("phase,index,n,bitmask,weight,threshold,interval,kind"));
    let trials=lines.map(|l|{let f=l.split(',').collect::<Vec<_>>();assert_eq!(f.len(),8);
        assert_eq!(f[2].parse::<usize>().unwrap(),n);
        (f[0].to_owned(),f[1].parse::<usize>().unwrap(),f[3].parse::<u64>().unwrap(),
            f[if predicate=="threshold" {5} else {6}].parse::<u64>().unwrap())
    }).collect::<Vec<_>>();
    assert_eq!(trials.len(),35);assert_eq!(trials.iter().filter(|x|x.0=="warmup").count(),5);
    let setup=Instant::now();let (cks,sks)=gen_keys(PARAM_MESSAGE_2_CARRY_4_KS_PBS);
    let threshold=predicate=="threshold";
    let lut=sks.generate_lookup_table(move |sum| if threshold {u64::from(sum>=n as u64/2)} else {u64::from((n as u64/3..=2*n as u64/3).contains(&sum))});
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("META,method=DCC_sum_bits_one_PBS,parameter=PARAM_MESSAGE_2_CARRY_4_KS_PBS,n={n},predicate={predicate},warmups=5,samples=30,rayon_threads={}",rayon::current_num_threads());
    println!("META,input=separately_encrypted_bits,output=one_shortint_bit,timing=checked_sum_plus_one_PBS,excluded=keygen_publicLUT_encryption_decryption,max_noise_level=21,logical_span={n},manifest={path}");
    println!("phase,index,n,bitmask,expected,actual,pbs_count,total_ms,input_degree,input_noise");
    for (phase,index,mask,expected) in trials {
        assert!(mask<(1<<n));
        let inputs=(0..n).map(|i|cks.encrypt((mask>>i)&1)).collect::<Vec<_>>();
        reset_pbs_count();let start=Instant::now();
        let mut sum=inputs[0].clone();
        for ct in inputs.iter().skip(1){sum=sks.checked_add(&sum,ct).expect("sum exceeds calibrated shortint budget");}
        let degree=sum.degree.get();let noise=sum.noise_level().get();
        assert!(degree<=63 && noise<=21);
        let result=black_box(sks.apply_lookup_table(&sum,&lut));
        let ms=start.elapsed().as_secs_f64()*1000.0;let pbs=get_pbs_count();
        let actual=cks.decrypt(&result);
        println!("{phase},{index},{n},{mask},{expected},{actual},{pbs},{ms:.6},{degree},{noise}");
        assert_eq!(actual,expected);assert_eq!(pbs,1);
    }
    println!("COMPLETE,measured=30,warmups=5,mismatches=0");
}
