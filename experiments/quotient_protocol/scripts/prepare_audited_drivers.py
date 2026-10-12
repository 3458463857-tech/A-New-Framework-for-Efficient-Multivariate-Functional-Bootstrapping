"""Only replace experiment selection/aggregation in the technical-audit candidates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
helper='''
fn read_protocol_manifest(t:u64)->Result<Vec<(String,usize,u64,u64)>,String>{
    let path=env::var("DCC_INPUT_MANIFEST").map_err(|_|"DCC_INPUT_MANIFEST is required")?;
    let text=std::fs::read_to_string(&path).map_err(|e|e.to_string())?;
    let mut lines=text.lines();
    if lines.next()!=Some("phase,index,t,m,d,kind"){return Err("bad manifest header".into());}
    let mut result=Vec::new();
    for line in lines {
        let f=line.split(',').collect::<Vec<_>>();
        if f.len()!=6{return Err("bad manifest row".into());}
        let parse=|s:&str|s.parse::<u64>().map_err(|e|e.to_string());
        let row_t=parse(f[2])?;let m=parse(f[3])?;let d=parse(f[4])?;
        if row_t!=t || m>=t || !(1..t).contains(&d){return Err("manifest domain error".into());}
        result.push((f[0].to_owned(),parse(f[1])? as usize,m,d));
    }
    if result.len()!=35 || result.iter().filter(|x|x.0=="warmup").count()!=5 || result.iter().filter(|x|x.0=="measured").count()!=30 {
        return Err("protocol requires 5 warmup and 30 measured rows".into());
    }
    println!("PROTOCOL,manifest={path},warmups=5,measured=30,rayon_threads={}",rayon::current_num_threads());
    Ok(result)
}
'''
audit=[]
for name,targ in [('algorithm1_t16_audited.rs','T'),('algorithm1_audited.rs','config.t')]:
    src=ROOT.parent/'correctness_audit/code'/name
    text=src.read_text(encoding='utf-8')
    original=text
    a=text.index('    let all_cases = deterministic_cases(')
    b=text.index('    let mut total_ms = 0.0;',a)
    text=text[:a]+f'    let selected=read_protocol_manifest({targ})?;\n    let measured_count=selected.iter().filter(|x|x.0=="measured").count();\n\n'+text[b:]
    text=text.replace('for (index, (dividend, divisor)) in selected.iter().copied().enumerate() {','for (phase,index,dividend,divisor) in selected.iter().cloned() {')
    text=text.replace('        total_ms += result.elapsed_ms;\n        total_pbs += result.pbs_count;','        if phase=="measured" {total_ms += result.elapsed_ms; total_pbs += result.pbs_count;}')
    text=text.replace('ENCRYPTED_RESULT,index={index}','ENCRYPTED_RESULT,phase={phase},index={index}').replace('ENCRYPTED_STAGES,index={index}','ENCRYPTED_STAGES,phase={phase},index={index}')
    text=text.replace('selected.len(),','measured_count,').replace('selected.len() as f64','measured_count as f64')
    text+=helper
    # All algorithm/trait code outside fn run() remains byte-identical (apart from appended I/O helper).
    def remove_run(s):
        begin=s.index('fn run() -> Result<(), String> {')
        end=s.index('\nfn main() -> ExitCode',begin)
        return s[:begin]+s[end:]
    assert remove_run(original)==remove_run(text[:-len(helper)])
    dest=ROOT/'source/section3/src/bin'/name
    dest.write_text(text,encoding='utf-8',newline='\n')
    audit.append({'source':str(src),'candidate_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
                  'final_path':str(dest),'final_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                  'algorithm_and_budget_trait_unchanged':True})
out=ROOT/'provenance';out.mkdir(exist_ok=True)
(out/'audited_driver_changes.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
print(json.dumps(audit,indent=2))
