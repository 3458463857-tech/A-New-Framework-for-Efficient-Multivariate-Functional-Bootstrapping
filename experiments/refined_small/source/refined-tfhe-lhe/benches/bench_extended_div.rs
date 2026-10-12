// Four encrypted 4-bit inputs -> all 16 CBS selectors -> two 16-to-4 LUTs.
// Author INT_LHE_BASE_16 algorithms and output precision are unchanged.
// Public high-bit padding is retained, including its full online cost.
use refined_tfhe_lhe::*;
use refined_tfhe_lhe::int_lhe_instance::INT_LHE_BASE_16;
use tfhe::core_crypto::prelude::*;
use tfhe::core_crypto::fft_impl::fft64::{c64, crypto::wop_pbs::{vertical_packing, vertical_packing_scratch}};
use std::time::Instant;
use std::hint::black_box;

fn mask2(x: usize) -> usize { x ^ ((x & 2) >> 1) ^ ((x & 8) >> 1) }

fn main() {
    let t:usize=std::env::args().nth(1).expect("t required").parse().unwrap();
    assert!([32,64].contains(&t));
    let param = *INT_LHE_BASE_16;
    let glwe_size = param.glwe_dimension().to_glwe_size();
    let n = param.polynomial_size();
    let modulus = param.ciphertext_modulus();
    let cbs_bl = param.cbs_base_log();
    let cbs_level = param.cbs_level();
    let delta = 1u64 << 59;
    let input_path=std::env::args().nth(2).expect("usage: bench_extended_div t INPUT_MANIFEST.csv");
    let input_text=std::fs::read_to_string(&input_path).expect("read manifest");
    let mut manifest_lines=input_text.lines();
    assert_eq!(manifest_lines.next(),Some("phase,index,t,m,d,kind"));
    let trials=manifest_lines.map(|line| {
        let f=line.split(',').collect::<Vec<_>>();
        assert_eq!(f.len(),6); assert_eq!(f[2].parse::<usize>().unwrap(),t);
        (f[0].to_owned(),f[1].parse::<usize>().unwrap(),f[3].parse::<usize>().unwrap(),f[4].parse::<usize>().unwrap())
    }).collect::<Vec<_>>();
    assert_eq!(trials.len(),35);
    assert_eq!(trials.iter().filter(|r|r.0=="warmup").count(),5);
    assert_eq!(trials.iter().filter(|r|r.0=="measured").count(),30);
    assert!(trials.iter().all(|r|r.2<t && (1..t).contains(&r.3)));
    let encode8=|x:usize| mask2(x&15) | (mask2(x>>4)<<4);
    // CBS extract_size=2 produces the mask2 encoding of each 4-bit block.
    // The public LUT includes every padded 16-bit index, including d=0 -> 0.
    let lut = (0..65536).map(|i| {
        let m=encode8(i&255); let d=encode8(i>>8);
        if d==0 {0u64} else {(m/d) as u64}
    }).collect::<Vec<_>>();
    for m in 0..256 { for d in 1..256 {
        assert_eq!(lut[encode8(m)+(encode8(d)<<8)],(m/d) as u64);
    }}
    println!("META,adapter=author_4block_CBS_then_two_16to4_vertical_packing_DIV,upstream_commit=9b0426e8e197020a4bf40776cc03641e6cf9b90e,param=INT_LHE_BASE_16,extract_size=2,warmups=5,samples=30,features=default_monothread");
    println!("META,input=four_4bit_no_padding_LWE_mlo_mhi_dlo_dhi,input_delta=2^60,output=two_4bit_padded_LWE_qlo_qhi,output_delta=2^59,public_LUT_entries_per_output=65536,public_LUT_polynomials_per_output=32,d_zero_entry=0_not_tested,t={t}");
    println!("META,n=769,N=2048,k=1,pbs_base_log=15,pbs_level=2,ks_base_log=4,ks_level=3,auto_base_log=7,auto_level=7,ss_base_log=17,ss_level=2,cbs_base_log=4,cbs_level=4,log_lut_count=2");
    println!("META,wall_timing=all_online_LWE_to_LWE_including_allocations_and_accumulator_reset,excluded=keygen_public_LUT_setup_encryption_decryption,cryptographic_randomness=fresh_OS_seed_unrecorded");
    println!("META,protocol=round2_B4_fixed_inputs_v4_extension,input_manifest={input_path},seed=20261026,measured_sampling=10_boundary_plus_20_SplitMix64_rejection_samples");
    let setup = Instant::now();
    let mut boxed_seeder = new_seeder();
    let seeder = boxed_seeder.as_mut();
    let mut secret_generator = SecretRandomGenerator::<ActivatedRandomGenerator>::new(seeder.seed());
    let mut encryption_generator = EncryptionRandomGenerator::<ActivatedRandomGenerator>::new(seeder.seed(), seeder);
    let (lwe_sk, glwe_sk, lwe_sk_after_ks, bsk, _unused_ksk) = keygen_pbs(
        param.lwe_dimension(), param.glwe_dimension(), n,
        param.lwe_modular_std_dev(), param.glwe_modular_std_dev(),
        param.pbs_base_log(), param.pbs_level(), param.ks_base_log(), param.ks_level(),
        &mut secret_generator, &mut encryption_generator);
    let bsk = bsk.as_view();
    // Retain the explicit key switch key construction in the author's integer-input bench.
    let ksk = allocate_and_generate_new_lwe_keyswitch_key(&lwe_sk, &lwe_sk_after_ks,
        param.ks_base_log(), param.ks_level(), param.lwe_modular_std_dev(), modulus,
        &mut encryption_generator);
    let auto_keys = gen_all_auto_keys(param.auto_base_log(), param.auto_level(),
        param.fft_type_auto(), &glwe_sk, param.glwe_modular_std_dev(), &mut encryption_generator);
    let ss_key_owned = generate_scheme_switching_key(&glwe_sk, param.ss_base_log(),
        param.ss_level(), param.glwe_modular_std_dev(), modulus, &mut encryption_generator);
    let ss_key = ss_key_owned.as_view();
    // Public identity accumulators can be prepared offline. Runtime clones are timed.
    let identity = (0..2).map(|idx| {
        let log_scale=60+idx*2;
        let plain=PlaintextList::from_container((0..n.0).map(|i| {
            if i<4 { let v=if i<2 { i } else { 2+(3-i) }; (v as u64)<<log_scale } else {0}
        }).collect::<Vec<_>>());
        allocate_and_trivially_encrypt_new_glwe_ciphertext(glwe_size,&plain,modulus)
    }).collect::<Vec<_>>();
    let polynomials=65536/n.0;
    let public_luts=(0..2).map(|part| {
        let mut list=PolynomialList::new(0u64,n,PolynomialCount(polynomials));
        for (coefficient,value) in list.as_mut().iter_mut().zip(lut.iter()) {
            *coefficient=((value>>(4*part))&15)*delta;
        }
        list
    }).collect::<Vec<_>>();
    let fft_owned=Fft::new(n); let fft=fft_owned.as_view();
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("phase,index,t,m,d,expected,actual,total_ms,input_conversion_ms,lut_ms,abs_error_lo,abs_error_hi");
    for (phase,index,m,d) in &trials {
        let inputs=[*m&15,*m>>4,*d&15,*d>>4].iter().map(|&value| allocate_and_encrypt_new_lwe_ciphertext(
            &lwe_sk,Plaintext((value as u64)<<60),param.glwe_modular_std_dev(),modulus,
            &mut encryption_generator)).collect::<Vec<_>>();
        let start=Instant::now();
        let mut selectors=GgswCiphertextList::new(0u64,glwe_size,n,cbs_bl,cbs_level,GgswCiphertextCount(16),modulus);
        for (mut operand_selectors,lwe) in selectors.chunks_exact_mut(4).zip(inputs.iter()) {
            let mut buf=lwe.clone();
            for (idx,mut chunk) in operand_selectors.chunks_exact_mut(2).enumerate() {
                let mut acc_glev=GlweCiphertextList::new(0u64,glwe_size,n,GlweCiphertextCount(cbs_level.0),modulus);
                let mut lwe_extract=LweCiphertext::new(0u64,buf.lwe_size(),modulus);
                lwe_ciphertext_cleartext_mul(&mut lwe_extract,&buf,Cleartext(1u64<<(4-2*(idx+1))));
                let mut lwe_extract_ks=LweCiphertext::new(0u64,ksk.output_lwe_size(),modulus);
                keyswitch_lwe_ciphertext(&ksk,&lwe_extract,&mut lwe_extract_ks);
                blind_rotate_for_msb(&lwe_extract_ks,&mut acc_glev,bsk,param.log_lut_count(),cbs_bl,cbs_level,2,modulus);
                let mut chunk_fourier=FourierGgswCiphertextList::new(
                    vec![c64::default();2*n.to_fourier_polynomial_size().0*glwe_size.0*glwe_size.0*cbs_level.0],
                    2,glwe_size,n,cbs_bl,cbs_level);
                let mut ct0=identity[idx].clone();
                let mut ct1=GlweCiphertext::new(0u64,glwe_size,n,modulus);
                for (i,(mut ggsw,mut fourier)) in chunk.iter_mut().zip(chunk_fourier.as_mut_view().into_ggsw_iter()).enumerate() {
                    convert_to_ggsw_after_blind_rotate(&acc_glev,&mut ggsw,2-i-1,&auto_keys,ss_key,modulus);
                    convert_standard_ggsw_ciphertext_to_fourier(&ggsw,&mut fourier);
                    glwe_ciphertext_monic_monomial_div(&mut ct1,&ct0,MonomialDegree(1<<i));
                    cmux_assign(&mut ct0,&mut ct1,&fourier);
                }
                let mut extracted=LweCiphertext::new(0u64,lwe.lwe_size(),modulus);
                extract_lwe_sample_from_glwe_ciphertext(&ct0,&mut extracted,MonomialDegree(0));
                let mut next=LweCiphertext::new(0u64,buf.lwe_size(),modulus);
                lwe_ciphertext_sub(&mut next,&buf,&extracted);
                buf=next;
            }
        }
        let mut fourier_selectors=FourierGgswCiphertextList::new(
            vec![c64::default();16*n.to_fourier_polynomial_size().0*glwe_size.0*glwe_size.0*cbs_level.0],
            16,glwe_size,n,cbs_bl,cbs_level);
        // This extra conversion is included, not hidden in offline setup.
        // Author vertical_packing expects selectors in MSB-first order.
        for (ggsw,mut fourier) in selectors.iter().rev().zip(fourier_selectors.as_mut_view().into_ggsw_iter()) {
            convert_standard_ggsw_ciphertext_to_fourier(&ggsw,&mut fourier);
        }
        let conversion_ms=start.elapsed().as_secs_f64()*1000.0;
        let lut_start=Instant::now();
        let outputs=public_luts.iter().map(|public_lut| {
            let mut output=LweCiphertext::new(0u64,lwe_sk.lwe_dimension().to_lwe_size(),modulus);
            // Fresh output and scratch allocation for each of the two LUTs, timed.
            let mut buffer=ComputationBuffers::new();
            buffer.resize(vertical_packing_scratch::<u64>(glwe_size,n,
                PolynomialCount(polynomials),16,fft).unwrap().unaligned_bytes_required());
            vertical_packing(public_lut.as_view(),output.as_mut_view(),
                fourier_selectors.as_view(),fft,buffer.stack());
            black_box(&output);
            output
        }).collect::<Vec<_>>();
        let lut_ms=lut_start.elapsed().as_secs_f64()*1000.0;
        let total_ms=start.elapsed().as_secs_f64()*1000.0;
        let expected=(m/d) as u64;
        let (lo,err_lo)=get_val_and_abs_err(&lwe_sk,&outputs[0],expected&15,delta);
        let (hi,err_hi)=get_val_and_abs_err(&lwe_sk,&outputs[1],expected>>4,delta);
        let actual=lo+(hi<<4);
        println!("{phase},{index},{t},{m},{d},{expected},{actual},{total_ms:.6},{conversion_ms:.6},{lut_ms:.6},{err_lo},{err_hi}");
        assert_eq!(actual,expected,"independent encrypted DIV query failed");
    }
    println!("COMPLETE,measured=30,warmups=5,mismatches=0");
}
