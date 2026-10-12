"""Prepare only; does not compile, execute, or benchmark the adapter."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
previous=root.parent/'experiments_refined_extended/source/refined-tfhe-lhe'
dest=root/'source/refined-tfhe-lhe'
if dest.exists(): raise SystemExit('Refusing existing destination')
shutil.copytree(previous,dest)
old=(previous/'benches/bench_extended_div.rs').read_text()
setup=old[old.index('    let setup = Instant::now();'):old.index('    let polynomials=65536/n.0;')]
cbs=old[old.index('        let mut selectors=GgswCiphertextList'):old.index('        let mut fourier_selectors=FourierGgswCiphertextList')]
cbs=cbs.replace('GgswCiphertextCount(16)','GgswCiphertextCount(width)').replace('zip(inputs.iter())','zip(packed.iter())')
prefix=r'''// Separately encrypted inputs -> timed public linear packing -> author integer CBS.
// Uses INT_LHE_BASE_16 unchanged. No client-computed statistic or selectors.
use refined_tfhe_lhe::*;
use refined_tfhe_lhe::int_lhe_instance::INT_LHE_BASE_16;
use tfhe::core_crypto::prelude::*;
use tfhe::core_crypto::fft_impl::fft64::{c64,crypto::wop_pbs::{vertical_packing,vertical_packing_scratch}};
use std::{time::Instant,hint::black_box};

fn mask2(x:usize)->usize {x ^ ((x&2)>>1) ^ ((x&8)>>1)}
fn dimensions(task:&str)->(usize,usize,bool) {
    match task {
        "hamming10_interval" => (10,2,true),
        "symbol6_interval_odd" | "symbol6_threshold_even" => (6,4,false),
        "median6_ternary" | "mode6_ternary" => (6,3,false),
        _=>panic!("Unknown task: {task}")
    }
}
fn evaluate(task:&str,x:&[usize])->u64 {
    match task {
        "hamming10_interval" => u64::from((4..=6).contains(&x.iter().sum::<usize>())),
        "symbol6_interval_odd" => u64::from((2..=4).contains(&x.iter().filter(|&&v|v==1||v==3).count())),
        "symbol6_threshold_even" => u64::from(x.iter().filter(|&&v|v==0||v==2).count()>=3),
        "median6_ternary" => {let mut v=x.to_vec();v.sort_unstable();v[2] as u64},
        "mode6_ternary" => {
            let mut counts=[0usize;3]; for &v in x {counts[v]+=1;}
            let mut best=0; for i in 1..3 {if counts[i]>counts[best] {best=i;}}
            best as u64
        },
        _=>unreachable!()
    }
}
fn main(){
    let task=std::env::args().nth(1).expect("task required");
    let input_path=std::env::args().nth(2).expect("manifest required");
    let (arity,domain,count_path)=dimensions(&task);
    let width=if count_path {4} else {12};
    let param=*INT_LHE_BASE_16;
    let glwe_size=param.glwe_dimension().to_glwe_size();
    let n=param.polynomial_size();let modulus=param.ciphertext_modulus();
    let cbs_bl=param.cbs_base_log();let cbs_level=param.cbs_level();let delta=1u64<<59;
    let input_text=std::fs::read_to_string(&input_path).expect("read manifest");
    let mut lines=input_text.lines();
    assert_eq!(lines.next(),Some("phase,index,task,values,expected,kind"));
    let trials=lines.map(|line|{
        let f=line.split(',').collect::<Vec<_>>();assert_eq!(f.len(),6);assert_eq!(f[2],task);
        let values=f[3].split(';').map(|v|v.parse::<usize>().unwrap()).collect::<Vec<_>>();
        assert_eq!(values.len(),arity);assert!(values.iter().all(|&v|v<domain));
        let expected=f[4].parse::<u64>().unwrap();assert_eq!(expected,evaluate(&task,&values));
        (f[0].to_owned(),f[1].parse::<usize>().unwrap(),values,expected)
    }).collect::<Vec<_>>();
    assert_eq!(trials.len(),35);
    assert_eq!(trials.iter().filter(|r|r.0=="warmup").count(),5);
    assert_eq!(trials.iter().filter(|r|r.0=="measured").count(),30);
    let entries=1usize<<width;
    let lut=(0..entries).map(|encoded|{
        if count_path {return u64::from((4..=6).contains(&mask2(encoded)));}
        let unpacked=(0..3).fold(0usize,|acc,j|acc|(mask2((encoded>>(4*j))&15)<<(4*j)));
        let values=(0..6).map(|j|(unpacked>>(2*j))&3).collect::<Vec<_>>();
        // The unused ternary digit 3 has a public, arbitrary extension value 0.
        if values.iter().any(|&v|v>=domain) {0} else {evaluate(&task,&values)}
    }).collect::<Vec<_>>();
    let domain_size=domain.pow(arity as u32);
    for encoded_input in 0..domain_size {
        let mut v=encoded_input;let mut values=Vec::new();
        for _ in 0..arity {values.push(v%domain);v/=domain;}
        let index=if count_path {mask2(values.iter().sum())} else {
            (0..3).fold(0usize,|acc,j|acc|(mask2(values[2*j]+4*values[2*j+1])<<(4*j)))
        };
        assert_eq!(lut[index],evaluate(&task,&values));
    }
    println!("META,task={task},adapter=online_linear_packing_integer_CBS_LUT,param=INT_LHE_BASE_16,arity={arity},symbol_domain={domain},input_delta=2^60,output_delta=2^59,output_blocks=1,selector_bits={width},plaintext_domain_verified={domain_size}");
    println!("META,timing=all_online_packing_CBS_Fourier_LUT_allocations,excluded=keygen_public_LUT_encryption_decryption,warmups=5,samples=30,default_feature=monothread,manifest={input_path}");
    println!("META,input_interface=independent_symbols_in_4bit_LWE_containers,no_free_rescaling_from_delta2^62,packing={}",if count_path {"sum_of_ten_encrypted_bits"} else {"three_ciphertext_pairs_c0_plus_4c1"});
'''
middle=r'''    let polynomials=if count_path {1} else {entries/n.0};
    let mut public_lut=PolynomialList::new(0u64,n,PolynomialCount(polynomials));
    for (i,coefficient) in public_lut.as_mut().iter_mut().enumerate(){
        *coefficient=if i<entries {lut[i]*delta} else {0};
    }
    let plain=PlaintextList::from_container(public_lut.as_ref()[..n.0].to_vec());
    let public_accumulator=allocate_and_trivially_encrypt_new_glwe_ciphertext(glwe_size,&plain,modulus);
    let fft_owned=Fft::new(n);let fft=fft_owned.as_view();
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("phase,index,task,values,expected,actual,total_ms,packing_ms,input_conversion_ms,lut_ms,abs_error");
    for (phase,index,values,expected) in &trials {
        let inputs=values.iter().map(|&v|allocate_and_encrypt_new_lwe_ciphertext(&lwe_sk,
            Plaintext((v as u64)<<60),param.glwe_modular_std_dev(),modulus,&mut encryption_generator)).collect::<Vec<_>>();
        let start=Instant::now();
        let packed=if count_path {
            let mut sum=LweCiphertext::new(0u64,lwe_sk.lwe_dimension().to_lwe_size(),modulus);
            for input in &inputs {lwe_ciphertext_add_assign(&mut sum,input);}
            vec![sum]
        } else {
            inputs.chunks_exact(2).map(|pair|{
                let mut sum=LweCiphertext::new(0u64,lwe_sk.lwe_dimension().to_lwe_size(),modulus);
                lwe_ciphertext_cleartext_mul(&mut sum,&pair[1],Cleartext(4));
                lwe_ciphertext_add_assign(&mut sum,&pair[0]);sum
            }).collect::<Vec<_>>()
        };
        let packing_ms=start.elapsed().as_secs_f64()*1000.0;
'''
suffix=r'''        let mut fourier_selectors=FourierGgswCiphertextList::new(
            vec![c64::default();width*n.to_fourier_polynomial_size().0*glwe_size.0*glwe_size.0*cbs_level.0],
            width,glwe_size,n,cbs_bl,cbs_level);
        let mut ordered=selectors.iter().collect::<Vec<_>>();
        if !count_path {ordered.reverse();} // Vertical packing uses MSB first.
        for (ggsw,mut fourier) in ordered.iter().zip(fourier_selectors.as_mut_view().into_ggsw_iter()) {
            convert_standard_ggsw_ciphertext_to_fourier(ggsw,&mut fourier);
        }
        let input_conversion_ms=start.elapsed().as_secs_f64()*1000.0-packing_ms;
        let lut_start=Instant::now();
        let mut output=LweCiphertext::new(0u64,lwe_sk.lwe_dimension().to_lwe_size(),modulus);
        if count_path {
            let mut accumulator=public_accumulator.clone();
            for (bit_idx,fourier) in fourier_selectors.as_view().into_ggsw_iter().enumerate(){
                let mut buf=accumulator.clone();
                glwe_ciphertext_monic_monomial_div_assign(&mut buf,MonomialDegree(1<<bit_idx));
                cmux_assign(&mut accumulator,&mut buf,&fourier);
            }
            extract_lwe_sample_from_glwe_ciphertext(&accumulator,&mut output,MonomialDegree(0));
        } else {
            let mut buffer=ComputationBuffers::new();
            buffer.resize(vertical_packing_scratch::<u64>(glwe_size,n,PolynomialCount(polynomials),width,fft).unwrap().unaligned_bytes_required());
            vertical_packing(public_lut.as_view(),output.as_mut_view(),fourier_selectors.as_view(),fft,buffer.stack());
        }
        black_box(&output);
        let lut_ms=lut_start.elapsed().as_secs_f64()*1000.0;
        let total_ms=start.elapsed().as_secs_f64()*1000.0;
        let (actual,error)=get_val_and_abs_err(&lwe_sk,&output,*expected,delta);
        let encoded_values=values.iter().map(|v|v.to_string()).collect::<Vec<_>>().join(";");
        println!("{phase},{index},{task},{encoded_values},{expected},{actual},{total_ms:.6},{packing_ms:.6},{input_conversion_ms:.6},{lut_ms:.6},{error}");
        assert_eq!(actual,*expected,"Encrypted function evaluation mismatch");
    }
    println!("COMPLETE,measured=30,warmups=5,mismatches=0");
}
'''
(dest/'benches/bench_functions.rs').write_text(prefix+setup+middle+cbs+suffix,encoding='utf-8',newline='\n')
with (dest/'Cargo.toml').open('a',encoding='utf-8',newline='\n') as f:
    f.write('\n[[bench]]\nname = "bench_functions"\nharness = false\n')
print('Prepared',dest/'benches/bench_functions.rs')
print('No build or encrypted evaluation was launched.')
