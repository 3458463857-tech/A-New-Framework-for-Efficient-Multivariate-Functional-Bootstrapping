//! Separately encrypted symbols -> original BBR evaluator -> one field output.
#[path="../files.rs"] mod files;
#[path="../decomposition.rs"] mod decomposition;
use std::{env,fs,time::Instant,io::Write};
use serde::Deserialize;
use serde_json::json;
use tfhe::gadget::prelude::*;
use decomposition::Decomposition;

#[derive(Deserialize)] struct Atom { alpha:Vec<u64>, lut:Vec<u64> }
#[derive(Deserialize)] struct Certificate {
    task_id:String, alphabet:u64, n:usize, p:u64, author_nu:usize,
    atoms:Vec<Atom>, output_beta:Vec<u64>,
}

fn main() {
    let a:Vec<_>=env::args().collect();
    assert_eq!(a.len(),4,"usage: matched_small_functions CERTIFICATE.json MANIFEST.csv OUTPUT.jsonl");
    let cert:Certificate=serde_json::from_str(&fs::read_to_string(&a[1]).unwrap()).unwrap();
    assert_eq!(cert.p,17); assert!(cert.author_nu>=5);
    let params=files::import_parameters_from_table(cert.p,cert.author_nu,128).unwrap();
    let dec=Decomposition::from_explicit_atoms(cert.n,cert.p,
        cert.atoms.iter().map(|x|(x.alpha.clone(),x.lut.clone())).collect(),
        cert.output_beta.clone(),params);
    let mut reader=csv::Reader::from_path(&a[2]).unwrap();
    assert_eq!(reader.headers().unwrap().iter().collect::<Vec<_>>(),
        vec!["phase","index","task_id","inputs","expected","kind"]);
    let rows:Vec<_>=reader.records().map(|x|x.unwrap()).collect();
    assert_eq!(rows.len(),35); assert_eq!(rows.iter().filter(|r|&r[0]=="warmup").count(),5);
    let mut out=fs::OpenOptions::new().write(true).create_new(true).open(&a[3]).unwrap();
    println!("PARAMETERS {}",serde_json::to_string(&dec.parameters).unwrap());
    println!("CERTIFICATE {}",json!({"task_id":cert.task_id,"p":cert.p,"author_nu":cert.author_nu,
        "atom_count":cert.atoms.len(),"final_linear_terms":cert.output_beta.iter().sum::<u64>(),
        "scope":"explicit structured decomposition, original author homomorphic evaluator"}));
    let (cks,sks)=gen_keys(&dec.parameters);
    let encoding=Encoding::new_trivial(cert.p);
    for row in rows {
        assert_eq!(&row[2],cert.task_id);
        let plain:Vec<u64>=row[3].split(';').map(|s|s.parse().unwrap()).collect();
        assert_eq!(plain.len(),cert.n); assert!(plain.iter().all(|x|*x<cert.alphabet));
        let expected:u64=row[4].parse().unwrap();
        let encrypted:Vec<_>=plain.iter().map(|x|cks.encrypt_arithmetic(*x,&encoding)).collect();
        let start=Instant::now();
        let result=dec.partial_lut_evaluation(&encrypted,&sks,1,&cks);
        let ms=start.elapsed().as_secs_f64()*1000.0;
        let actual=cks.decrypt_arithmetic(&result[0],&dec.encodings[0]);
        let record=json!({"phase":&row[0],"index":row[1].parse::<usize>().unwrap(),
            "task_id":cert.task_id,"inputs":plain,"expected":expected,"actual":actual,
            "correct":actual==expected,"elapsed_ms":ms,"kind":&row[5]});
        writeln!(out,"{}",record).unwrap();out.flush().unwrap();println!("{}",record);
        assert_eq!(actual,expected,"Completed records retained on failure");
    }
}
