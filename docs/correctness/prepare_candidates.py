from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent
old=here.parent.parent/'DCC_revision_2026-10-10_v1/05_Reproducibility/code/Section3_Code/src'
dest=here/'code';dest.mkdir(parents=True,exist_ok=True)
s=(old/'bin/algorithm1_noise_checked.rs').read_text(encoding='utf-8-sig')
def exact_tables(t,m):
    ns=[a**m for a in range(1,t)]
    return ([0]+[n.bit_length()-int(n&(n-1)==0)+1 for n in ns],
            [1]+[n.bit_length() for n in ns])
tables={44:exact_tables(32,44),89:exact_tables(64,89)}
start=s.index('fn shifted_ceil(');end=s.index('fn make_config(',start)
replacement='// Exact finite-domain tables generated from integer powers by prepare_candidates.py.\n'
for name,idx in [('shifted_ceil',0),('shifted_floor',1)]:
    replacement+=f'fn {name}(value: u64, scale: u64) -> u64 {{\n    match scale {{\n'
    for scale,pair in tables.items():
        replacement+=f'        {scale} => '+str(pair[idx])+'[value as usize],\n'
    replacement+='        _ => panic!("unsupported exact integer scale"),\n    }\n}\n\n'
s=s[:start]+replacement+s[end:]
s=s.replace('    let encrypted_m_high = shortint_cks.unchecked_encrypt(dividend / INPUT_CHUNK);','    let mut encrypted_m_high = shortint_cks.unchecked_encrypt(dividend / INPUT_CHUNK);\n    // Public-domain bound: both high chunks are at most input_branches - 1.\n    encrypted_m_high.degree = Degree::new(config.input_branches - 1);')
s=s.replace('    let encrypted_d_high = shortint_cks.unchecked_encrypt(divisor / INPUT_CHUNK);','    let mut encrypted_d_high = shortint_cks.unchecked_encrypt(divisor / INPUT_CHUNK);\n    encrypted_d_high.degree = Degree::new(config.input_branches - 1);')
s=s.replace('        assert_shortint_budget(input, "many-LUT PBS input");','        assert_shortint_budget(input, "many-LUT PBS input");\n        assert!(input.degree.get() <= lut.input_max_degree.get(),\n            "many-LUT-specific input range exceeded");')
s=s.replace('    sks.add_parallelized(&base, &residual)\n}', '    let result = sks.add_parallelized(&base, &residual);\n    assert_nominal_radix(&result, "final radix addition output");\n    result\n}')
s=s.replace('    let outer_ms = outer_started.elapsed()', '    assert_nominal_radix(&quotient, "quotient output");\n    let outer_ms = outer_started.elapsed()')
(dest/'algorithm1_audited.rs').write_text(s,encoding='utf-8')

t=(old/'main.rs').read_text(encoding='utf-8-sig')
t='// Round-2 audited t=16 variant; original source is preserved in v1.\n'+t
for a,b in (('.apply_lookup_table(','.budget_lut('),('.unchecked_apply_lookup_table_bivariate(','.budget_bivariate('),('.unchecked_add_assign(','.budget_add_assign('),('.unchecked_scalar_mul_assign(','.budget_scalar_mul_assign(')):
    t=t.replace(a,b)
t=t.replace('    let shifted_delta = sks.sub_parallelized(&encrypted_ceil, &encrypted_floor);','    assert_nominal_radix(&encrypted_ceil, "radix subtraction left");\n    assert_nominal_radix(&encrypted_floor, "radix subtraction right");\n    let shifted_delta = sks.sub_parallelized(&encrypted_ceil, &encrypted_floor);\n    assert_nominal_radix(&shifted_delta, "radix subtraction output");')
t=t.replace('    partial_sum_refresh: LookupTableOwned,','    partial_sum_refresh: LookupTableOwned,\n    final_refresh: LookupTableOwned,')
# Public LUT setup remains outside the timer.
needle='partial_sum_refresh: shortint_sks.generate_lookup_table('
pos=t.find(needle)
if pos<0:
    needle='partial_sum_refresh:';pos=t.rfind(needle)
end=t.index('\n',pos)
t=t[:end]+ '\n        final_refresh: shortint_sks.generate_lookup_table(|value| value),' + t[end:]
t=t.replace('    let elapsed_ms = started.elapsed()', '    // The final linear sum has noise level 4; refresh under the level-5 budget.\n    quotient = shortint_sks.budget_lut(&quotient, &luts.final_refresh);\n    assert!(quotient.noise_level().get() <= 1 && quotient.degree.get() <= 15);\n    let elapsed_ms = started.elapsed()')
# Reuse exactly the audited wrappers, omitting methods unused by t=16.
trait=s[s.index('// Explicit metadata contracts'):]
trait=trait.replace('ManyLookupTableOwned','ManyLookupTableOwned')
t=t.replace('use tfhe::shortint::server_key::{BivariateLookupTableOwned, LookupTableOwned};','use tfhe::shortint::server_key::{BivariateLookupTableOwned, LookupTableOwned, ManyLookupTableOwned};')
t+='\n'+trait
(dest/'algorithm1_t16_audited.rs').write_text(t,encoding='utf-8')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.glob('*.rs')}
(here/'candidate_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
