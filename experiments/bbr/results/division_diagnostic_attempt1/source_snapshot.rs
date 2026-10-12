//! Diagnostic only: decrypt each stage of the unchanged author evaluator.
//! This program must never be used for benchmark timings.
#[path="../files.rs"] mod files;
#[path="../decomposition.rs"] mod decomposition;
use std::{env,fs,io::Write,path::Path};
use serde_json::{json,Value};
use tfhe::gadget::prelude::*;
use tfhe::core_crypto::prelude::{LweCiphertext,CiphertextModulus};

fn emit(out:&mut fs::File,v:Value){writeln!(out,"{}",v).unwrap();out.flush().unwrap();println!("{}",v);}
fn plain(v:&[u64],a:&[u64])->u64 {v.iter().zip(a).map(|(x,y)|x*y).sum::<u64>()%17}
fn weighted(v:&Vec<Ciphertext>,a:&[u64],s:&ServerKey)->Ciphertext {
    s.simple_sum(&v.iter().zip(a).map(|(x,y)|s.simple_mul_constant(x,*y,17)).collect())
}
fn check(out:&mut fs::File,label:String,c:&Ciphertext,e:u64,k:&ClientKey)->u64 {
    let actual=k.decrypt_arithmetic(c,&Encoding::new_trivial(17));
    emit(out,json!({"stage":label,"expected":e,"actual":actual,"correct":actual==e,
       "author_measure_noise_scaled":k.measure_noise(c)}));actual
}
fn pbs(out:&mut fs::File,label:String,c:&Ciphertext,arg:u64,lut:&[u64],k:&ClientKey,s:&ServerKey,first:&mut bool)->Ciphertext {
    let e=Encoding::new_trivial(17);
    let decoded=k.decrypt_arithmetic(c,&e);
    let result=s.apply_lut(c,&e,&|x|lut[x as usize]);
    let actual=check(out,label.clone(),&result,lut[arg as usize],k);
    emit(out,json!({"stage":format!("{}.local_contract",label),"argument_expected":arg,
        "argument_decoded":decoded,"expected_from_decoded_argument":lut[decoded as usize],
        "output_decoded":actual,"local_correct":actual==lut[decoded as usize]}));
    if actual!=lut[decoded as usize] && !*first {
        *first=true;
        for z in 0..17u64 {
            let fresh=k.encrypt_arithmetic(z,&e);
            let fresh_out=s.apply_lut(&fresh,&e,&|x|lut[x as usize]);
            let ideal=match &fresh {Ciphertext::EncodingEncrypted(ct,_)=>{
                let mut c0=LweCiphertext::new(0u64,ct.lwe_size(),CiphertextModulus::new_native());
                *c0.get_mut_body().data=(((1u128<<64)/17)*(z as u128)) as u64;
                Ciphertext::EncodingEncrypted(c0,e.clone())},_=>unreachable!()};
            let ideal_out=s.apply_lut(&ideal,&e,&|x|lut[x as usize]);
            emit(out,json!({"stage":format!("{}.fresh_and_zero_mask_control",label),"input":z,
               "expected":lut[z as usize],"fresh_actual":k.decrypt_arithmetic(&fresh_out,&e),
               "zero_mask_actual":k.decrypt_arithmetic(&ideal_out,&e)}));
        }
    }
    result
}
fn main(){
    let args:Vec<_>=env::args().collect();
    assert_eq!(args.len(),5,"diagnose_division DECOMPOSITION_NAME OUT.jsonl m d");
    let dec=decomposition::Decomposition::load_decomposition(4,17,2,128,&args[1]);
    let p=Path::new(env!("CARGO_MANIFEST_DIR")).join("../../decompositions").join(&args[1]);
    let (l,ts,_)=files::read_parameters_decompositions(&p.join("parameters_17_2"));
    let phis=files::read_phis_from_file(&p.join("new_phis_17_2")).unwrap();
    let beta=files::read_betas(&p.join("betas_17_2")).unwrap();
    let gamma=files::read_gammas(&p.join("d_17_2")).unwrap();
    let m=args[3].parse::<u64>().unwrap();let d=args[4].parse::<u64>().unwrap();
    let mut out=fs::OpenOptions::new().write(true).create_new(true).open(&args[2]).unwrap();
    emit(&mut out,json!({"parameters":dec.parameters,"m":m,"d":d,"diagnostic_only":true}));
    let (k,s)=gen_keys(&dec.parameters);let e=Encoding::new_trivial(17);
    let inputs=vec![k.encrypt_arithmetic(m,&e),k.encrypt_arithmetic(d,&e)];
    let mut xs=inputs.clone();let mut clear=vec![m,d];let mut first=false;
    for (i,c) in xs.iter().enumerate(){check(&mut out,format!("input.{}",i),c,clear[i],&k);}
    for i in 0..l {
        let (alpha,lut)=&phis[&(-1,i)];let arg=plain(&clear,alpha);let sum=weighted(&xs,alpha,&s);
        check(&mut out,format!("atom.{}.weighted_input",i),&sum,arg,&k);
        let output=pbs(&mut out,format!("atom.{}.pbs",i),&sum,arg,lut,&k,&s,&mut first);
        xs.push(output);clear.push(lut[arg as usize]);
    }
    let ni=2+l;let mut products=vec![];let mut plain_products=vec![];
    for j in 0..ts[0] {
        let a=&beta[0][j*ni..(j+1)*ni];let b=&gamma[0][j*ni..(j+1)*ni];
        let left=weighted(&xs,a,&s);let right=weighted(&xs,b,&s);
        let lc=plain(&clear,a);let rc=plain(&clear,b);
        check(&mut out,format!("product.{}.left",j),&left,lc,&k);
        check(&mut out,format!("product.{}.right",j),&right,rc,&k);
        let plus=s.simple_sum(&vec![left.clone(),right.clone()]);
        check(&mut out,format!("product.{}.plus_argument",j),&plus,(lc+rc)%17,&k);
        let minus=s.simple_sum(&[vec![left.clone()],vec![right.clone();16]].concat());
        check(&mut out,format!("product.{}.minus_literal_argument",j),&minus,(lc+16*rc)%17,&k);
        let lutp:Vec<_>=(0..17u64).map(|x|x*x*13%17).collect();
        let lutm:Vec<_>=(0..17u64).map(|x|16*x*x*13%17).collect();
        let pp=pbs(&mut out,format!("product.{}.plus_pbs",j),&plus,(lc+rc)%17,&lutp,&k,&s,&mut first);
        let mp=pbs(&mut out,format!("product.{}.minus_pbs",j),&minus,(lc+16*rc)%17,&lutm,&k,&s,&mut first);
        let prod=s.simple_sum(&vec![pp,mp]);
        check(&mut out,format!("product.{}.result",j),&prod,lc*rc%17,&k);
        products.push(prod);plain_products.push(lc*rc%17);
    }
    let linear=weighted(&xs,&beta[0][ts[0]*ni..],&s);
    let linear_clear=plain(&clear,&beta[0][ts[0]*ni..]);
    check(&mut out,"final.linear".into(),&linear,linear_clear,&k);
    products.push(linear);let result=s.simple_sum(&products);
    let target=(plain_products.iter().sum::<u64>()+linear_clear)%17;
    assert_eq!(target,if d==0 {0}else{m/d});
    check(&mut out,"final.output".into(),&result,target,&k);
    let original=dec.partial_lut_evaluation(&inputs,&s,1,&k);
    let identical=match (&original[0],&result){(Ciphertext::EncodingEncrypted(a,_),Ciphertext::EncodingEncrypted(b,_))=>a.as_ref()==b.as_ref(),_=>false};
    emit(&mut out,json!({"stage":"original_evaluator_crosscheck","bitwise_identical":identical,
      "original_actual":k.decrypt_arithmetic(&original[0],&dec.encodings[0]),"expected":target}));
    assert!(identical,"Diagnostic must faithfully mirror the original evaluator");
}
