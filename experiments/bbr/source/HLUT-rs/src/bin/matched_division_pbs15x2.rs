//! Original author evaluator and certificate; PBS decomposition changed to (15,2).
//! Dimensions, noise distributions, KS, encoding and online evaluation are unchanged.
#[path="../files.rs"] mod files;
#[path="../decomposition.rs"] mod decomposition;
use std::{env,fs,time::Instant,io::Write};
use serde_json::json;
use tfhe::gadget::prelude::*;
use decomposition::Decomposition;

fn main() {
    let a:Vec<_>=env::args().collect();
    assert_eq!(a.len(),4,"usage: matched_division DECOMPOSITION_NAME MANIFEST.csv OUTPUT.jsonl");
    let mut dec=Decomposition::load_decomposition(4,17,2,128,&a[1]);
    dec.parameters.pbs_base_log=DecompositionBaseLog(15);
    dec.parameters.pbs_level=DecompositionLevelCount(2);
    assert_eq!(dec.sbox.len(),256);
    for d in 0..16usize {for m in 0..16usize {
        assert_eq!(dec.sbox[m+16*d],if d==0 {0} else {(m/d) as u64});
    }}
    let mut reader=csv::Reader::from_path(&a[2]).unwrap();
    assert_eq!(reader.headers().unwrap().iter().collect::<Vec<_>>(),
               vec!["phase","index","t","m","d","kind"]);
    let rows:Vec<_>=reader.records().map(|x|x.unwrap()).collect();
    assert_eq!(rows.len(),35);assert_eq!(rows.iter().filter(|r|&r[0]=="warmup").count(),5);
    let mut out=fs::OpenOptions::new().write(true).create_new(true).open(&a[3]).unwrap();
    println!("PARAMETERS {}",serde_json::to_string(&dec.parameters).unwrap());
    let (cks,sks)=gen_keys(&dec.parameters);
    let encoding=Encoding::new_trivial(17);
    for row in rows {
        assert_eq!(&row[2],"16");
        let m:u64=row[3].parse().unwrap();let d:u64=row[4].parse().unwrap();
        assert!(m<16 && d>0 && d<16);
        let encrypted=vec![cks.encrypt_arithmetic(m,&encoding),cks.encrypt_arithmetic(d,&encoding)];
        let start=Instant::now();
        let result=dec.partial_lut_evaluation(&encrypted,&sks,1,&cks);
        let ms=start.elapsed().as_secs_f64()*1000.0;
        let actual=cks.decrypt_arithmetic(&result[0],&dec.encodings[0]);
        let expected=m/d;
        let record=json!({"phase":&row[0],"index":row[1].parse::<usize>().unwrap(),
            "t":16,"m":m,"d":d,"expected":expected,"actual":actual,
            "correct":actual==expected,"elapsed_ms":ms,"kind":&row[5]});
        writeln!(out,"{}",record).unwrap();out.flush().unwrap();println!("{}",record);
        assert_eq!(actual,expected,"Completed records retained on failure");
    }
}
