//! Matched-workload timing harness; author homomorphic evaluator remains intact.
#[path="../files.rs"] mod files;
#[path="../decomposition.rs"] mod decomposition;
use std::{env, fs, time::Instant};
use tfhe::gadget::prelude::*;
use decomposition::Decomposition;
use serde_json::json;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 { panic!("usage: matched_tasks count-threshold|count-interval|division INPUT.csv OUTPUT.jsonl"); }
    let task=&args[1]; let input_path=&args[2]; let output_path=&args[3];
    assert!(!std::path::Path::new(output_path).exists(), "refusing to overwrite records");
    let mut rdr=csv::Reader::from_path(input_path).unwrap();
    let rows:Vec<_>=rdr.records().map(|r|r.unwrap()).collect();
    assert_eq!(rows.len(),35); assert_eq!(rows.iter().filter(|r|&r[0]=="warmup").count(),5);
    let p=17;
    let dec=if task.starts_with("count-") {
        let n=rows[0][2].parse::<usize>().unwrap();
        let parameters=files::import_parameters_from_table(p,5,128).unwrap();
        Decomposition::certified_count(n, task=="count-interval", parameters)
    } else {
        assert_eq!(task,"division"); assert_eq!(&rows[0][2],"16");
        Decomposition::load_decomposition(4,p,2,128,"division_t16")
    };
    println!("PARAMETERS {}",serde_json::to_string(&dec.parameters).unwrap());
    let (cks,sks)=gen_keys(&dec.parameters);
    let encoding=Encoding::new_trivial(p);
    let mut output=fs::OpenOptions::new().write(true).create_new(true).open(output_path).unwrap();
    use std::io::Write;
    for row in rows {
        let n=row[2].parse::<usize>().unwrap();
        let (plain,expected,task_input)=if task.starts_with("count-") {
            let bits=row[3].parse::<u64>().unwrap();
            let plain:Vec<u64>=(0..n).map(|i|(bits>>i)&1).collect();
            let e=row[if task=="count-interval"{6}else{5}].parse::<u64>().unwrap();
            (plain,e,json!({"n":n,"bitmask":bits,"weight":row[4].parse::<u64>().unwrap()}))
        } else {
            let m=row[3].parse::<u64>().unwrap();let d=row[4].parse::<u64>().unwrap();
            (vec![m,d],m/d,json!({"t":n,"m":m,"d":d}))
        };
        let encrypted:Vec<_>=plain.iter().map(|m|cks.encrypt_arithmetic(*m,&encoding)).collect();
        let start=Instant::now();
        let result=dec.partial_lut_evaluation(&encrypted,&sks,1,&cks);
        let elapsed_ms=start.elapsed().as_secs_f64()*1000.0;
        let actual=cks.decrypt_arithmetic(&result[0],&dec.encodings[0]);
        let record=json!({"phase":&row[0],"index":row[1].parse::<usize>().unwrap(),
            "task":task,"input":task_input,"expected":expected,"actual":actual,
            "correct":actual==expected,"elapsed_ms":elapsed_ms});
        writeln!(output,"{}",record).unwrap(); output.flush().unwrap();
        println!("{}",record);
        assert_eq!(actual,expected,"homomorphic output mismatch; completed records retained");
    }
}
