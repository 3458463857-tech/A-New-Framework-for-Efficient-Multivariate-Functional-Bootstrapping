"""Derive the fixed small-capacity driver without altering any earlier source."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent
OLD=V5/'experiments_ours_multibit'
src=OLD/'ours/src/bin/functions_checked.rs'
text=src.read_text()
def change(old,new):
    global text
    assert old in text,old
    text=text.replace(old,new)
change('Existing group-three multi-bit backend; same circuit as the frozen classic run.',
       'Fixed small-capacity group-three implementation; two symbols per inner PBS.')
change('PARAM_MULTI_BIT_GROUP_3_MESSAGE_1_CARRY_4_KS_PBS_GAUSSIAN_2M64',
       'PARAM_MULTI_BIT_GROUP_3_MESSAGE_1_CARRY_3_KS_PBS_GAUSSIAN_2M64')
change('PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_4_KS_PBS_GAUSSIAN_2M64',
       'PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_2_KS_PBS_GAUSSIAN_2M64')
change('use tfhe::shortint::parameters::multi_bit::p_fail_2_minus_64::ks_pbs::{',
       'use tfhe::shortint::parameters::multi_bit::p_fail_2_minus_64::ks_pbs::{PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_3_KS_PBS_GAUSSIAN_2M64, ')
change('[7, 0, 5][x as usize]', '[self.n as u64 + 1, 0, self.n as u64][x as usize]')
for old,new in [('lower_median3_6','lower_median3_3'),('mode3_6','mode3_4'),('max3_6','max3_3'),('range3_6','range3_3'),('iqr3_6','iqr3_4'),('mad3_6','mad3_3'),('distinct3_6','distinct3_3')]:
    change(f'Task{{id:"{old}",t:3,n:6,',f'Task{{id:"{new}",t:3,n:{4 if new.endswith("_4") else 3},')
change('if task.direct_sum(){1}else{3}','if task.direct_sum(){1}else{task.n.div_ceil(2)+1}')
change('assert_eq!(pbs,if task.direct_sum(){1}else{task.n.div_ceil(2)+1});',
       'assert_eq!(pbs,(if task.direct_sum(){1}else{task.n.div_ceil(2)+1}) as u64);')
change('"m1c4" => (PARAM_MULTI_BIT_GROUP_3_MESSAGE_1_CARRY_3_KS_PBS_GAUSSIAN_2M64,Budget{capacity:32,max_noise:31,message:2}),',
       '"m1c3" => (PARAM_MULTI_BIT_GROUP_3_MESSAGE_1_CARRY_3_KS_PBS_GAUSSIAN_2M64,Budget{capacity:16,max_noise:15,message:2}),')
change('"m2c4" => (PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_2_KS_PBS_GAUSSIAN_2M64,Budget{capacity:64,max_noise:21,message:4}),',
       '"m2c2" => (PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_2_KS_PBS_GAUSSIAN_2M64,Budget{capacity:16,max_noise:5,message:4}),\n        "m2c3" => (PARAM_MULTI_BIT_GROUP_3_MESSAGE_2_CARRY_3_KS_PBS_GAUSSIAN_2M64,Budget{capacity:32,max_noise:10,message:4}),')
change('parameter must be m1c4 or m2c4','parameter must be m1c3, m2c2 or m2c3')
change('parameter=="m2c4", "nonbinary packing requires m2c4"',
       '(parameter=="m2c2" || parameter=="m2c3"), "nonbinary packing requires a message modulus of four"')
change('(0..task.n/3).map(|_|{\n            let task=task.clone();',
       '(0..task.n).step_by(2).map(|first|{\n            let take=(task.n-first).min(2);\n            let task=task.clone();')
change('for _ in 0..3{sum+=task.score', 'for _ in 0..take{sum+=task.score')
change('assert_eq!(task.n%3,0);', 'assert!(task.n>=2);')
change('inputs.chunks(3).zip', 'inputs.chunks(2).zip')
change('META,backend=multi_bit_group_3,producer_threads', 'META,backend=multi_bit_group_3,packing_group_size=2,producer_threads')
dest=ROOT/'ours/src/bin/functions_checked.rs';dest.parent.mkdir(parents=True,exist_ok=True)
assert not dest.exists(),'refuse to overwrite a prepared source'
dest.write_text(text,newline='\n')
for name in ['Cargo.toml','Cargo.lock']:shutil.copyfile(OLD/'ours'/name,ROOT/'ours'/name)
shutil.copyfile(OLD/'scripts/build_ours.sh',ROOT/'scripts/build_ours.sh')
inputs=ROOT/'inputs';inputs.mkdir(exist_ok=True)
base=ROOT.parents[1]/'DCC_submission_polish_v4/experiments_functions/inputs'
for name in ['hamming_interval10','set_interval4_6','set_threshold4_6']:shutil.copyfile(base/(name+'.csv'),inputs/(name+'.csv'))
for f in (V5/'experiments_small_functions/inputs').glob('*.csv'):shutil.copyfile(f,inputs/f.name)
provenance=ROOT/'provenance';provenance.mkdir(exist_ok=True)
(provenance/'source_derivation.json').write_text(json.dumps(dict(parent_source=str(src),parent_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),derived_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changes=['fixed published smaller parameters','two-symbol inner grouping with actual last-group arity','seven explicitly new small-domain tasks','uniform histogram score (n+1,0,n)','dynamic exact PBS-count assertions']),indent=2)+'\n')
print('Prepared fixed capacity driver; no encrypted evaluation')
