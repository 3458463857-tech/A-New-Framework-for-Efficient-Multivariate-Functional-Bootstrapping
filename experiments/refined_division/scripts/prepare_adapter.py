"""Create a standalone extension of the frozen R2 adapter; never edit R2 files."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
old = root.parents[1] / 'DCC_targeted_revision_v2' / 'final_experiments'
dest = root / 'source' / 'refined-tfhe-lhe'
if dest.exists():
    raise SystemExit('Refusing to overwrite existing source')
shutil.copytree(old / 'source/refined-tfhe-lhe', dest)
(root / 'inputs').mkdir(exist_ok=True)
for t in (32, 64):
    shutil.copy2(old / f'inputs/division_t{t}.csv', root / f'inputs/division_t{t}.csv')
s = (dest / 'benches/bench_targeted_div4.rs').read_text(encoding='utf-8')
def replace(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
replace('// Targeted revision adapter, 2026-10-10. Author library algorithms are unchanged.\n// Composes bench_integer_input_lhe.rs (improved, extract_size=2) with\n// bench_lut_eval.rs (8-to-4 CMUX LUT). See ../../../README.md for timing scope.',
'''// Four encrypted 4-bit inputs -> all 16 CBS selectors -> two 16-to-4 LUTs.
// Author INT_LHE_BASE_16 algorithms and output precision are unchanged.
// Public high-bit padding is retained, including its full online cost.''')
replace('use tfhe::core_crypto::fft_impl::fft64::c64;', 'use tfhe::core_crypto::fft_impl::fft64::{c64, crypto::wop_pbs::{vertical_packing, vertical_packing_scratch}};')
replace('    let param = *INT_LHE_BASE_16;', '''    let t:usize=std::env::args().nth(1).expect("t required").parse().unwrap();
    assert!([32,64].contains(&t));
    let param = *INT_LHE_BASE_16;''')
replace('std::env::args().nth(1).expect("usage: bench_targeted_div4 INPUT_MANIFEST.csv")', 'std::env::args().nth(2).expect("usage: bench_extended_div t INPUT_MANIFEST.csv")')
replace('assert_eq!(f[2],"16");', 'assert_eq!(f[2].parse::<usize>().unwrap(),t);')
replace('r.2<16 && (1..16).contains(&r.3)', 'r.2<t && (1..t).contains(&r.3)')
replace('''    let lut = (0..256).map(|i| {
        let m=mask2(i & 15); let d=mask2(i >> 4);
        if d == 0 { 0u64 } else { (m/d) as u64 }
    }).collect::<Vec<_>>();
    for m in 0..16 { for d in 1..16 { assert_eq!(lut[mask2(m)+16*mask2(d)], (m/d) as u64); } }''', '''    let encode8=|x:usize| mask2(x&15) | (mask2(x>>4)<<4);
    // CBS extract_size=2 produces the mask2 encoding of each 4-bit block.
    // The public LUT includes every padded 16-bit index, including d=0 -> 0.
    let lut = (0..65536).map(|i| {
        let m=encode8(i&255); let d=encode8(i>>8);
        if d==0 {0u64} else {(m/d) as u64}
    }).collect::<Vec<_>>();
    for m in 0..256 { for d in 1..256 {
        assert_eq!(lut[encode8(m)+(encode8(d)<<8)],(m/d) as u64);
    }}''')
replace('author_CBS_then_CMUX_DIV4', 'author_4block_CBS_then_two_16to4_vertical_packing_DIV')
replace('input=two_4bit_no_padding_LWE,input_delta=2^60,output=4bit_padded_LWE,output_delta=2^59,public_LUT_entries=256,d_zero_entry=0_not_tested', 'input=four_4bit_no_padding_LWE_mlo_mhi_dlo_dhi,input_delta=2^60,output=two_4bit_padded_LWE_qlo_qhi,output_delta=2^59,public_LUT_entries_per_output=65536,public_LUT_polynomials_per_output=32,d_zero_entry=0_not_tested,t={t}')
replace('protocol=round2_B4,input_manifest={input_path},seed=20261026', 'protocol=round2_B4_fixed_inputs_v4_extension,input_manifest={input_path},seed=20261026')
replace('''    let public_plain = PlaintextList::from_container((0..n.0).map(|i| if i<256 { lut[i]*delta } else {0}).collect::<Vec<_>>());
    let public_accumulator = allocate_and_trivially_encrypt_new_glwe_ciphertext(glwe_size,&public_plain,modulus);''', '''    let polynomials=65536/n.0;
    let public_luts=(0..2).map(|part| {
        let mut list=PolynomialList::new(0u64,n,PolynomialCount(polynomials));
        for (coefficient,value) in list.as_mut().iter_mut().zip(lut.iter()) {
            *coefficient=((value>>(4*part))&15)*delta;
        }
        list
    }).collect::<Vec<_>>();
    let fft_owned=Fft::new(n); let fft=fft_owned.as_view();''')
replace('println!("phase,index,m,d,expected,actual,total_ms,input_conversion_ms,lut_ms,abs_error");', 'println!("phase,index,t,m,d,expected,actual,total_ms,input_conversion_ms,lut_ms,abs_error_lo,abs_error_hi");')
replace('let inputs=[*m,*d].iter()', 'let inputs=[*m&15,*m>>4,*d&15,*d>>4].iter()')
replace('GgswCiphertextCount(8)', 'GgswCiphertextCount(16)')
replace('vec![c64::default();8*n.to_fourier_polynomial_size().0*glwe_size.0*glwe_size.0*cbs_level.0],\n            8,glwe_size,n,cbs_bl,cbs_level);', 'vec![c64::default();16*n.to_fourier_polynomial_size().0*glwe_size.0*glwe_size.0*cbs_level.0],\n            16,glwe_size,n,cbs_bl,cbs_level);')
replace('for (ggsw,mut fourier) in selectors.iter().zip(', '// Author vertical_packing expects selectors in MSB-first order.\n        for (ggsw,mut fourier) in selectors.iter().rev().zip(')
start=s.index('        // Fresh accumulator per independent query')
end=s.index('        assert_eq!(actual,expected,"independent encrypted DIV query failed");',start)
s=s[:start]+'''        let outputs=public_luts.iter().map(|public_lut| {
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
''' + s[end:]
(dest / 'benches/bench_extended_div.rs').write_text(s,encoding='utf-8',newline='\n')
with (dest / 'Cargo.toml').open('a',encoding='utf-8',newline='\n') as f:
    f.write('\n[[bench]]\nname = "bench_extended_div"\nharness = false\n')
print(dest)
