"""Select the existing fresh-input API; keep unmeasured packing draft separate."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'source/refined-tfhe-lhe'
path=source/'benches/bench_functions.rs'
s=path.read_text()
assert 'online_linear_packing_integer_CBS_LUT' in s
names={'hamming10_interval':'hamming_interval10','symbol6_interval_odd':'set_interval4_6',
       'symbol6_threshold_even':'set_threshold4_6','median6_ternary':'lower_median3_6','mode6_ternary':'mode3_6'}
for a,b in names.items():s=s.replace(a,b)
draft=root/'drafts/bench_functions_packing_UNMEASURED.rs'
draft.parent.mkdir(exist_ok=True)
draft.write_text(s,encoding='utf-8',newline='\n')
def replace(a,b):
    global s
    assert s.count(a)==1,(a[:70],s.count(a))
    s=s.replace(a,b)
replace('// Separately encrypted inputs -> timed public linear packing -> author integer CBS.\n// Uses INT_LHE_BASE_16 unchanged. No client-computed statistic or selectors.',
'''// Fresh independent inputs -> author CBS -> public full LUT.
// Four-bit symbol CBS parameters are unchanged; known zero high selectors are omitted.
// Binary inputs use the author's BITWISE_CBS_CMUX3 path; no online input summing.''')
replace('use refined_tfhe_lhe::int_lhe_instance::INT_LHE_BASE_16;',
        'use refined_tfhe_lhe::int_lhe_instance::{INT_LHE_BASE_16,BITWISE_CBS_CMUX3};')
replace('let width=if count_path {4} else {12};','let width=if count_path {10} else {12};')
replace('let param=*INT_LHE_BASE_16;','let param=if count_path {*BITWISE_CBS_CMUX3} else {*INT_LHE_BASE_16};')
replace('let cbs_bl=param.cbs_base_log();let cbs_level=param.cbs_level();let delta=1u64<<59;',
'''let cbs_bl=param.cbs_base_log();let cbs_level=param.cbs_level();
    let input_scale=if count_path {63} else {60};
    let output_scale=if count_path {62} else {59};
    let delta=1u64<<output_scale;''')
replace('''        if count_path {return u64::from((4..=6).contains(&mask2(encoded)));}
        let unpacked=(0..3).fold(0usize,|acc,j|acc|(mask2((encoded>>(4*j))&15)<<(4*j)));
        let values=(0..6).map(|j|(unpacked>>(2*j))&3).collect::<Vec<_>>();''',
'''        if count_path {return u64::from((4..=6).contains(&(encoded.count_ones() as usize)));}
        let values=(0..6).map(|j|mask2((encoded>>(2*j))&3)).collect::<Vec<_>>();''')
replace('''        let index=if count_path {mask2(values.iter().sum())} else {
            (0..3).fold(0usize,|acc,j|acc|(mask2(values[2*j]+4*values[2*j+1])<<(4*j)))
        };''',
'''        let index=if count_path {(0..10).fold(0usize,|acc,j|acc|(values[j]<<j))} else {
            (0..6).fold(0usize,|acc,j|acc|(mask2(values[j])<<(2*j)))
        };''')
start=s.index('    println!("META,task=')
end=s.index('    let setup = Instant::now();',start)
s=s[:start]+'''    let parameter_name=if count_path {"BITWISE_CBS_CMUX3"} else {"INT_LHE_BASE_16"};
    println!("META,task={task},adapter=fresh_input_author_CBS_full_LUT,param={parameter_name},arity={arity},symbol_domain={domain},input_scale_log2={input_scale},output_scale_log2={output_scale},output_blocks=1,selector_bits={width},plaintext_domain_verified={domain_size}");
    println!("META,timing=all_online_CBS_Fourier_LUT_allocations,excluded=keygen_public_LUT_encryption_decryption,warmups=5,samples=30,default_feature=monothread,manifest={input_path}");
    println!("META,input_interface=independent_fresh_encrypted_inputs,no_linear_packing_or_statistic,no_client_selectors,unused_symbol_high_bits=public_zero");
''' +s[end:]
replace('Plaintext((v as u64)<<60)','Plaintext((v as u64)<<input_scale)')
start=s.index('        let packed=if count_path {')
end=s.index('        let mut fourier_selectors=',start)
original=s[s.index('        let mut selectors=GgswCiphertextList',start):end]
original=original.replace('GgswCiphertextCount(width)','GgswCiphertextCount(24)').replace('zip(packed.iter())','zip(inputs.iter())')
original=original.replace('        let mut selectors=GgswCiphertextList::new(0u64,glwe_size,n,cbs_bl,cbs_level,GgswCiphertextCount(24),modulus);\n','')
new='''        let packing_ms=0.0;
        let mut selectors=GgswCiphertextList::new(0u64,glwe_size,n,cbs_bl,cbs_level,
            GgswCiphertextCount(if count_path {10} else {24}),modulus);
        if count_path {
            for (input,mut selector) in inputs.iter().zip(selectors.iter_mut()) {
                let mut switched=LweCiphertext::new(0u64,ksk.output_lwe_size(),modulus);
                keyswitch_lwe_ciphertext(&ksk,input,&mut switched);
                let mut glev=GlweCiphertextList::new(0u64,glwe_size,n,GlweCiphertextCount(cbs_level.0),modulus);
                blind_rotate_for_msb(&switched,&mut glev,bsk,param.log_lut_count(),cbs_bl,cbs_level,1,modulus);
                convert_to_ggsw_after_blind_rotate(&glev,&mut selector,0,&auto_keys,ss_key,modulus);
            }
        } else {
'''+original+'''        }
'''
s=s[:start]+new+s[end:]
replace('let mut ordered=selectors.iter().collect::<Vec<_>>();',
'''// Every symbol was run through the unchanged full 4-bit CBS. Only its
        // two low selectors are used; its two high plaintext bits are public zero.
        let mut ordered=selectors.iter().enumerate().filter(|(i,_)|count_path||i%4<2)
            .map(|(_,ggsw)|ggsw).collect::<Vec<_>>();''')
path.write_text(s,encoding='utf-8',newline='\n')
print('Prepared fresh-input path. Packing draft is excluded from Cargo bench targets.')
print('No compilation or encrypted evaluation was launched.')
