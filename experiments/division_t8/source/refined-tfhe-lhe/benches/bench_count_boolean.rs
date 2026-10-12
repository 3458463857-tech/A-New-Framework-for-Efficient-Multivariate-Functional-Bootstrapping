//! Author bitwise CBS followed by author full-LUT vertical packing.
//! Fresh separately encrypted bit inputs; no client-computed selector or statistic.
use std::{env,fs,hint::black_box,time::Instant};
use refined_tfhe_lhe::*;
use refined_tfhe_lhe::int_lhe_instance::BITWISE_CBS_CMUX3;
use tfhe::core_crypto::prelude::*;
use tfhe::core_crypto::fft_impl::fft64::{c64,crypto::wop_pbs::{vertical_packing,vertical_packing_scratch}};

fn main(){
    let width:usize=env::args().nth(1).expect("width required").parse().unwrap();
    let predicate=env::args().nth(2).expect("predicate required");
    let path=env::args().nth(3).expect("manifest required");
    assert!([12,16].contains(&width));assert!(["threshold","interval"].contains(&predicate.as_str()));
    let text=fs::read_to_string(&path).unwrap();let mut lines=text.lines();
    assert_eq!(lines.next(),Some("phase,index,n,bitmask,weight,threshold,interval,kind"));
    let trials=lines.map(|l|{let f=l.split(',').collect::<Vec<_>>();assert_eq!(f.len(),8);
        assert_eq!(f[2].parse::<usize>().unwrap(),width);
        (f[0].to_owned(),f[1].parse::<usize>().unwrap(),f[3].parse::<u64>().unwrap(),
            f[if predicate=="threshold" {5} else {6}].parse::<u64>().unwrap())
    }).collect::<Vec<_>>();
    assert_eq!(trials.len(),35);assert_eq!(trials.iter().filter(|x|x.0=="warmup").count(),5);
    let p=*BITWISE_CBS_CMUX3;let n=p.polynomial_size();let gs=p.glwe_dimension().to_glwe_size();
    let modulus=p.ciphertext_modulus();let cbs_bl=p.cbs_base_log();let cbs_level=p.cbs_level();
    let delta=1u64<<62;let polynomials=(1usize<<width)/n.0;
    println!("META,method=Refined_Boolean_CBS_full_LUT,param=BITWISE_CBS_CMUX3,n={width},predicate={predicate},warmups=5,samples=30,features=default_monothread");
    println!("META,input=separately_encrypted_bigLWE_bits_delta2^63,output=one_padded_bigLWE_bit_delta2^62,timing=all_CBS_Fourier_vertical_packing_allocations,excluded=keygen_publicLUT_encryption_decryption,manifest={path}");
    println!("META,small_lwe_dimension=636,polynomial_size=2048,glwe_dimension=1,pbs=15/2,ks=2/5,auto=7/6_Split35,ss=17/2,cbs=4/4,log_lut_count=2,extract_size=1");
    println!("RESOURCE,logical_full_LUT_entries={},public_LUT_coefficient_bytes={},public_LUT_polynomials={polynomials}",1usize<<width,(1usize<<width)*8);
    let setup=Instant::now();let mut boxed_seeder=new_seeder();let seeder=boxed_seeder.as_mut();
    let mut sr=SecretRandomGenerator::<ActivatedRandomGenerator>::new(seeder.seed());
    let mut er=EncryptionRandomGenerator::<ActivatedRandomGenerator>::new(seeder.seed(),seeder);
    let (lwe_sk,glwe_sk,small_sk,bsk,_original_ksk)=keygen_pbs(p.lwe_dimension(),p.glwe_dimension(),n,
        p.lwe_modular_std_dev(),p.glwe_modular_std_dev(),p.pbs_base_log(),p.pbs_level(),p.ks_base_log(),p.ks_level(),&mut sr,&mut er);
    let bsk=bsk.as_view();
    let ksk=allocate_and_generate_new_lwe_keyswitch_key(&lwe_sk,&small_sk,p.ks_base_log(),p.ks_level(),p.lwe_modular_std_dev(),modulus,&mut er);
    let auto_keys=gen_all_auto_keys(p.auto_base_log(),p.auto_level(),p.fft_type_auto(),&glwe_sk,p.glwe_modular_std_dev(),&mut er);
    let ss_owned=generate_scheme_switching_key(&glwe_sk,p.ss_base_log(),p.ss_level(),p.glwe_modular_std_dev(),modulus,&mut er);
    let ss=ss_owned.as_view();let fft=Fft::new(n);let fft=fft.as_view();
    let mut lut=PolynomialList::new(0u64,n,PolynomialCount(polynomials));
    // The full-LUT index is the ordinary little-endian bitmask. Vertical packing
    // consumes selectors MSB first, as in the author's reversed GGSW assignment.
    for (i,coefficient) in lut.as_mut().iter_mut().enumerate(){
        let weight=i.count_ones() as usize;
        let output=if predicate=="threshold" {weight>=width/2} else {(width/3..=2*width/3).contains(&weight)};
        *coefficient=u64::from(output)*delta;
    }
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("phase,index,n,bitmask,expected,actual,total_ms,input_conversion_ms,lut_ms,abs_error");
    for (phase,index,mask,expected) in trials{
        assert!(mask<(1<<width));
        let inputs=(0..width).map(|i|allocate_and_encrypt_new_lwe_ciphertext(&lwe_sk,
            Plaintext(((mask>>i)&1)<<63),p.glwe_modular_std_dev(),modulus,&mut er)).collect::<Vec<_>>();
        let start=Instant::now();
        let mut selectors=GgswCiphertextList::new(0u64,gs,n,cbs_bl,cbs_level,GgswCiphertextCount(width),modulus);
        let mut fourier=FourierGgswCiphertextList::new(vec![c64::default();width*n.to_fourier_polynomial_size().0*gs.0*gs.0*cbs_level.0],width,gs,n,cbs_bl,cbs_level);
        for ((input,mut selector),mut out) in inputs.iter().rev().zip(selectors.iter_mut()).zip(fourier.as_mut_view().into_ggsw_iter()){
            let mut switched=LweCiphertext::new(0u64,ksk.output_lwe_size(),modulus);
            keyswitch_lwe_ciphertext(&ksk,input,&mut switched);
            let mut glev=GlweCiphertextList::new(0u64,gs,n,GlweCiphertextCount(cbs_level.0),modulus);
            blind_rotate_for_msb(&switched,&mut glev,bsk,p.log_lut_count(),cbs_bl,cbs_level,1,modulus);
            convert_to_ggsw_after_blind_rotate(&glev,&mut selector,0,&auto_keys,ss,modulus);
            convert_standard_ggsw_ciphertext_to_fourier(&selector,&mut out);
        }
        let input_ms=start.elapsed().as_secs_f64()*1000.0;let lut_start=Instant::now();
        let mut output=LweCiphertext::new(0u64,lwe_sk.lwe_dimension().to_lwe_size(),modulus);
        let mut buffer=ComputationBuffers::new();
        buffer.resize(vertical_packing_scratch::<u64>(gs,n,PolynomialCount(polynomials),width,fft).unwrap().unaligned_bytes_required());
        vertical_packing(lut.as_view(),output.as_mut_view(),fourier.as_view(),fft,buffer.stack());
        black_box(&output);
        let lut_ms=lut_start.elapsed().as_secs_f64()*1000.0;let total_ms=start.elapsed().as_secs_f64()*1000.0;
        let (actual,error)=get_val_and_abs_err(&lwe_sk,&output,expected,delta);
        println!("{phase},{index},{width},{mask},{expected},{actual},{total_ms:.6},{input_ms:.6},{lut_ms:.6},{error}");
        assert_eq!(actual,expected,"Boolean CBS -> full-LUT mismatch");
    }
    println!("COMPLETE,measured=30,warmups=5,mismatches=0");
}
