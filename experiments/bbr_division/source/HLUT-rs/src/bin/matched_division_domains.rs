//! BBR author evaluator on small or mixed domains, with revised PBS (15,2).
//! No decryption or target-dependent client operation occurs inside the timer.
#[path="../files.rs"] mod files;
#[path="../decomposition.rs"] mod decomposition;
use std::{env,fs,time::Instant,io::Write};
use serde_json::json;
use tfhe::gadget::prelude::*;
use decomposition::Decomposition;

fn main() {
    let a:Vec<_>=env::args().collect();
    assert_eq!(a.len(),5,"usage: matched_division_domains T DECOMPOSITION_NAME MANIFEST.csv OUTPUT.jsonl");
    let t:u64=a[1].parse().unwrap(); assert!(t==8 || t==32);
    let (log_s,n,outputs) = if t==8 {(3,2,1)} else {(4,4,2)};
    let mut dec=Decomposition::load_decomposition(log_s,17,n,128,&a[2]);
    // Same explicit repair as the successful t16 reproduction. The original
    // parameter-table failure estimate is NOT a claim for this revised setting.
    dec.parameters.pbs_base_log=DecompositionBaseLog(15);
    dec.parameters.pbs_level=DecompositionLevelCount(2);
    assert_eq!(dec.sbox.len(),(t*t) as usize);
    for d in 0..t {for m in 0..t {
        assert_eq!(dec.sbox[(m+t*d) as usize],if d==0 {0} else {m/d});
    }}
    let mut reader=csv::Reader::from_path(&a[3]).unwrap();
    assert_eq!(reader.headers().unwrap().iter().collect::<Vec<_>>(),
               vec!["phase","index","t","m","d","kind"]);
    let rows:Vec<_>=reader.records().map(|x|x.unwrap()).collect();
    assert_eq!(rows.len(),35); assert_eq!(rows.iter().filter(|r|&r[0]=="warmup").count(),5);
    assert_eq!(rows.iter().filter(|r|&r[0]=="measured").count(),30);
    let mut out=fs::OpenOptions::new().write(true).create_new(true).open(&a[4]).unwrap();
    println!("PARAMETERS {}",serde_json::to_string(&dec.parameters).unwrap());
    println!("TIMING all author online sums, accumulator encoding, KS/PBS, products and outputs; sequential evaluator, CPU affinity 0-7");
    let (cks,sks)=gen_keys(&dec.parameters);
    let encoding=Encoding::new_trivial(17);
    for row in rows {
        assert_eq!(row[2].parse::<u64>().unwrap(),t);
        let m:u64=row[3].parse().unwrap(); let d:u64=row[4].parse().unwrap();
        assert!(m<t && d>0 && d<t);
        let plain_inputs=if t==8 {vec![m,d]} else {vec![m%16,m/16,d%16,d/16]};
        let encrypted=plain_inputs.iter().map(|x|cks.encrypt_arithmetic(*x,&encoding)).collect();
        let start=Instant::now();
        let result=dec.partial_lut_evaluation(&encrypted,&sks,outputs,&cks);
        let ms=start.elapsed().as_secs_f64()*1000.0;
        let digits:Vec<u64>=result.iter().enumerate().map(|(i,x)|cks.decrypt_arithmetic(x,&dec.encodings[i])).collect();
        let actual=if t==8 {digits[0]} else {digits[0]+16*digits[1]};
        let expected=m/d;
        let record=json!({"phase":&row[0],"index":row[1].parse::<usize>().unwrap(),
            "t":t,"m":m,"d":d,"input_blocks":plain_inputs,"output_blocks":digits,
            "expected":expected,"actual":actual,"correct":actual==expected,
            "elapsed_ms":ms,"kind":&row[5]});
        writeln!(out,"{}",record).unwrap(); out.flush().unwrap(); println!("{}",record);
        assert_eq!(actual,expected,"Completed records retained on failure");
    }
}
