//! Native TFHE-rs division, matched public workload and 5+30 protocol.
use std::{env,fs,hint::black_box,time::Instant};
use tfhe::integer::{gen_keys_radix,RadixCiphertext,IntegerCiphertext};
use tfhe::shortint::parameters::PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS;
use tfhe::{get_pbs_count,reset_pbs_count};
fn main(){
    let t:u64=env::args().nth(1).expect("t required").parse().unwrap();
    let path=env::args().nth(2).expect("input manifest required");
    assert!([8].contains(&t));
    let text=fs::read_to_string(&path).unwrap();
    let mut lines=text.lines();assert_eq!(lines.next(),Some("phase,index,t,m,d,kind"));
    let trials=lines.map(|l|{let f=l.split(',').collect::<Vec<_>>();
        assert_eq!(f.len(),6);assert_eq!(f[2].parse::<u64>().unwrap(),t);
        (f[0].to_owned(),f[1].parse::<usize>().unwrap(),f[3].parse::<u64>().unwrap(),f[4].parse::<u64>().unwrap())
    }).collect::<Vec<_>>();
    assert_eq!(trials.len(),35);
    assert_eq!(trials.iter().filter(|x|x.0=="warmup").count(),5);
    assert_eq!(trials.iter().filter(|x|x.0=="measured").count(),30);
    let blocks=if t<=16 {2} else {3};
    let setup=Instant::now();
    let (cks,mut sks)=gen_keys_radix(PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,blocks);
    sks.set_deterministic_pbs_execution(false);
    let integer_cks:&tfhe::integer::ClientKey=cks.as_ref();
    let short_cks:&tfhe::shortint::ClientKey=integer_cks.as_ref();
    let short_sks:&tfhe::shortint::ServerKey=sks.as_ref();
    let low_lut=short_sks.generate_lookup_table(|x|x%4);
    let high_lut=short_sks.generate_lookup_table(|x|x/4);
    let identity_lut=short_sks.generate_lookup_table(|x|x);
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("META,method=native_div_parallelized,tfhe=0.8.7,t={t},blocks={blocks},parameter=PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,warmups=5,samples=30,rayon_threads={}",rayon::current_num_threads());
    println!("META,input=separate_low4bit_and_optional_high2bit_LWE_chunks,output=one_shortint,implementation_bits=4,logical_t=8,timing=online_chunk_to_radix_plus_div_parallelized_plus_output_conversion,excluded=encryption_decryption_keygen,manifest={path}");
    println!("phase,index,t,m,d,expected,actual,pbs_count,total_ms");
    for (phase,index,m,d) in trials {
        assert!(m<t && (1..t).contains(&d));
        let ml=short_cks.unchecked_encrypt(m%16);let dl=short_cks.unchecked_encrypt(d%16);
        let mh=if t>16 {Some(short_cks.encrypt(m/16))} else {None};
        let dh=if t>16 {Some(short_cks.encrypt(d/16))} else {None};
        reset_pbs_count();let start=Instant::now();
        let convert=|low:&tfhe::shortint::Ciphertext,high:Option<tfhe::shortint::Ciphertext>|{
            assert!(low.degree.get()<=15 && low.noise_level().get()<=5);
            let mut digits=vec![short_sks.apply_lookup_table(low,&low_lut),short_sks.apply_lookup_table(low,&high_lut)];
            if let Some(ct)=high {assert!(ct.degree.get()<=3 && ct.noise_level().get()<=1);digits.push(ct);}
            assert!(digits.iter().all(|ct|ct.degree.get()<=3 && ct.noise_level().get()<=1));
            RadixCiphertext::from(digits)
        };
        let (cm,cd)=rayon::join(||convert(&ml,mh),||convert(&dl,dh));
        let cq=black_box(sks.div_parallelized(&cm,&cd));
        assert!(cq.blocks().iter().all(|ct|ct.degree.get()<=3 && ct.noise_level().get()<=1));
        let single=if t<=16 {
            assert!(cq.blocks().iter().all(|ct|ct.degree.get()<=3 && ct.noise_level().get()<=1));
            let upper=short_sks.unchecked_scalar_mul(&cq.blocks()[1],4);
            let packed=short_sks.unchecked_add(&cq.blocks()[0],&upper);
            assert!(packed.degree.get()<=15 && packed.noise_level().get()<=5);
            Some(short_sks.apply_lookup_table(&packed,&identity_lut))
        } else {None};
        let ms=start.elapsed().as_secs_f64()*1000.0;let pbs=get_pbs_count();
        let actual:u64=if let Some(ct)=single {short_cks.decrypt_message_and_carry(&ct)} else {cks.decrypt(&cq)};let expected=m/d;
        println!("{phase},{index},{t},{m},{d},{expected},{actual},{pbs},{ms:.6}");
        assert_eq!(actual,expected);
    }
    println!("COMPLETE,measured=30,warmups=5,mismatches=0");
}
