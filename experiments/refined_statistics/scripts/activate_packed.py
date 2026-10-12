"""Activate the authorized packing interface; retain the fresh route as source."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'source/refined-tfhe-lhe/benches/bench_functions.rs'
alternative=root/'alternatives/bench_functions_fresh.rs'
alternative.parent.mkdir(exist_ok=True)
assert not alternative.exists()
alternative.write_text(path.read_text(),encoding='utf-8',newline='\n')
s=(root/'drafts/bench_functions_packing_UNMEASURED.rs').read_text()
s=s.replace('"median6_ternary"','"lower_median3_6"')
s=s.replace('"lower_median3_6" | "mode3_6" => (6,3,false),',
'''"lower_median3_6" | "mode3_6" | "max3_6" | "range3_6" |
        "iqr3_6" | "mad3_6" | "distinct3_6" => (6,3,false),''')
assert '"max3_6"' in s
needle='''        _=>unreachable!()
    }
}'''
assert s.count(needle)==1
s=s.replace(needle,'''        "max3_6" => *x.iter().max().unwrap() as u64,
        "range3_6" => (*x.iter().max().unwrap()-*x.iter().min().unwrap()) as u64,
        "iqr3_6" => {
            let mut v=x.to_vec();v.sort_unstable();
            // Frozen original definition: floor(3(n-1)/4) minus floor((n-1)/4).
            (v[3]-v[1]) as u64
        },
        "mad3_6" => {
            let mut v=x.to_vec();v.sort_unstable();let center=v[2];
            let mut deviations=x.iter().map(|&value|value.abs_diff(center)).collect::<Vec<_>>();
            deviations.sort_unstable();deviations[2] as u64
        },
        "distinct3_6" => {
            let mut present=[false;3];for &v in x {present[v]=true;}
            present.iter().filter(|&&v|v).count() as u64
        },
        _=>unreachable!()
    }
}''')
s=s.replace('phase,index,task,values,expected,kind','phase,index,task_id,inputs,expected,kind')
s=s.replace('phase,index,task,values,expected,actual,total_ms','phase,index,task_id,inputs,expected,actual,total_ms')
needle='''    let setup = Instant::now();'''
assert s.count(needle)==1
s=s.replace(needle,'''    println!("META,packing_input_variance_multiplier={},first_extraction_fresh_component_variance_multiplier={},whole_path_failure_bound=not_established_for_packing",if count_path {10} else {17},if count_path {160} else {272});
    let setup = Instant::now();''')
path.write_text(s,encoding='utf-8',newline='\n')
print('Activated authorized packed adapter for ten frozen functions; did not compile or run.')
