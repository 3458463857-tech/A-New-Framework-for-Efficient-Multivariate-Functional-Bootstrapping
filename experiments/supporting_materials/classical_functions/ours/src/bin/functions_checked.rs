//! Prepared benchmark: no homomorphic evaluation unless --run is explicit.
//! Each input is encrypted separately; every linear operation uses checked APIs.
use std::{collections::{BTreeMap, BTreeSet}, env, fs, hint::black_box, time::Instant};
use tfhe::{get_pbs_count, reset_pbs_count};
use tfhe::shortint::{gen_keys, Ciphertext, ServerKey};
use tfhe::shortint::parameters::{PARAM_MESSAGE_1_CARRY_4_KS_PBS, PARAM_MESSAGE_2_CARRY_4_KS_PBS};

#[derive(Clone, Copy, Debug)]
enum Target { HammingInterval, SetInterval, SetThreshold, Median, Mode, Max, Range, Iqr, Mad, Distinct }
#[derive(Clone, Debug)]
struct Task { id: &'static str, t: usize, n: usize, target: Target }
impl Task {
    fn direct_sum(&self) -> bool { self.t == 2 }
    fn output_max(&self) -> u64 {
        match self.target { Target::Median | Target::Mode | Target::Max | Target::Range | Target::Iqr | Target::Mad => 2, Target::Distinct => 3, _ => 1 }
    }
    fn score(&self, x: u64) -> u64 {
        match self.target {
            Target::SetInterval => u64::from(x == 1 || x == 3),
            Target::SetThreshold => u64::from(x == 0 || x == 2),
            _ if self.t == 3 => [7, 0, 5][x as usize],
            _ => x,
        }
    }
    fn target(&self, xs: &[u64]) -> u64 {
        assert_eq!(xs.len(), self.n);
        assert!(xs.iter().all(|&x| x < self.t as u64));
        let mut sorted = xs.to_vec(); sorted.sort_unstable();
        let sum: u64 = xs.iter().sum();
        let median = sorted[(self.n - 1) / 2];
        match self.target {
            Target::HammingInterval => u64::from((4..=6).contains(&sum)),
            Target::SetInterval => u64::from((2..=4).contains(&xs.iter().filter(|&&x| x == 1 || x == 3).count())),
            Target::SetThreshold => u64::from(xs.iter().filter(|&&x| x == 0 || x == 2).count() >= 3),
            Target::Median => median,
            Target::Mode => {
                let mut counts = vec![0; self.t]; for &x in xs { counts[x as usize] += 1; }
                let max = *counts.iter().max().unwrap(); counts.iter().position(|&n| n == max).unwrap() as u64
            },
            Target::Max => *sorted.last().unwrap(),
            Target::Range => sorted[self.n - 1] - sorted[0],
            Target::Iqr => sorted[3 * (self.n - 1) / 4] - sorted[(self.n - 1) / 4],
            Target::Mad => {
                let mut deviations: Vec<u64> = xs.iter().map(|&x| x.abs_diff(median)).collect();
                deviations.sort_unstable(); deviations[(self.n - 1) / 2]
            },
            Target::Distinct => xs.iter().collect::<BTreeSet<_>>().len() as u64,
        }
    }
}
fn tasks() -> Vec<Task> {
    use Target::*;
    vec![
        Task{id:"hamming_interval10",t:2,n:10,target:HammingInterval},
        Task{id:"set_interval4_6",t:4,n:6,target:SetInterval},
        Task{id:"set_threshold4_6",t:4,n:6,target:SetThreshold},
        Task{id:"lower_median3_6",t:3,n:6,target:Median},
        Task{id:"mode3_6",t:3,n:6,target:Mode},
        Task{id:"max3_6",t:3,n:6,target:Max},
        Task{id:"range3_6",t:3,n:6,target:Range},
        Task{id:"iqr3_6",t:3,n:6,target:Iqr},
        Task{id:"mad3_6",t:3,n:6,target:Mad},
        Task{id:"distinct3_6",t:3,n:6,target:Distinct},
    ]
}
fn enumerate<F: FnMut(&[u64])>(task: &Task, xs: &mut [u64], i: usize, f: &mut F) {
    if i == xs.len() { f(xs); return; }
    for x in 0..task.t as u64 { xs[i] = x; enumerate(task, xs, i + 1, f); }
}
// This checks the entire Cartesian input domain, not just the measured sample.
fn certify(task: &Task) -> (Vec<u64>, usize, usize, u64) {
    let mut values = BTreeMap::new(); let mut visited = 0;
    enumerate(task, &mut vec![0; task.n], 0, &mut |xs| {
        let score: u64 = xs.iter().map(|&x| task.score(x)).sum();
        let target = task.target(xs); assert!(target <= task.output_max());
        if let Some(previous) = values.insert(score, target) {
            assert_eq!(previous, target, "unequal target values collide in {} at {score}", task.id);
        }
        visited += 1;
    });
    assert_eq!(visited, task.t.pow(task.n as u32));
    let max = *values.keys().max().unwrap(); assert!(max < 64);
    let mut outer = vec![0; 64]; for (&score, &y) in &values { outer[score as usize] = y; }
    (outer, visited, values.len(), max)
}
#[derive(Clone, Copy)]
struct Budget { capacity: usize, max_noise: usize, message: u64 }
fn check(ct: &Ciphertext, budget: Budget, stage: &str) {
    assert!(ct.degree.get() < budget.capacity, "{stage}: degree out of range");
    assert!(ct.noise_level().get() <= budget.max_noise, "{stage}: noise level out of range");
}
fn checked_sum(sks: &ServerKey, cts: &[Ciphertext], budget: Budget) -> Ciphertext {
    assert!(!cts.is_empty()); let mut sum = cts[0].clone(); check(&sum, budget, "sum first");
    for ct in &cts[1..] {
        check(ct, budget, "sum operand");
        sum = sks.checked_add(&sum, ct).expect("checked accumulation rejected");
        check(&sum, budget, "sum result");
    }
    sum
}
struct Trial { phase: String, index: usize, inputs: Vec<u64>, expected: u64, kind: String }
fn load_trials(path: &str, task: &Task) -> Vec<Trial> {
    let text = fs::read_to_string(path).expect("cannot read input manifest");
    let mut lines = text.lines(); assert_eq!(lines.next(), Some("phase,index,task_id,inputs,expected,kind"));
    let mut seen = BTreeSet::new();
    let result: Vec<Trial> = lines.filter(|l| !l.trim().is_empty()).map(|line| {
        let f: Vec<_> = line.split(',').collect(); assert_eq!(f.len(), 6);
        assert_eq!(f[2], task.id); assert!(["warmup", "measured"].contains(&f[0]));
        let index = f[1].parse::<usize>().unwrap(); assert!(seen.insert((f[0].to_owned(), index)));
        let inputs: Vec<u64> = f[3].split(';').map(|x| x.parse().unwrap()).collect();
        let expected = f[4].parse().unwrap(); assert_eq!(task.target(&inputs), expected);
        Trial{phase:f[0].to_owned(),index,inputs,expected,kind:f[5].to_owned()}
    }).collect();
    assert_eq!(result.len(),35); assert_eq!(result.iter().filter(|t|t.phase=="warmup").count(),5);
    assert!(result[..5].iter().all(|t|t.phase=="warmup"));
    assert!(result[5..].iter().all(|t|t.phase=="measured"));
    result
}
fn arg(args: &[String], key: &str) -> String {
    let i = args.iter().position(|a|a==key).unwrap_or_else(||panic!("required argument {key}"));
    args.get(i+1).unwrap_or_else(||panic!("value required for {key}")).clone()
}
fn main() {
    let args: Vec<String> = env::args().collect();
    if args.iter().any(|x|x=="--list") {
        println!("task_id,t,n,output_max,pbs_count");
        for task in tasks(){println!("{},{},{},{},{}",task.id,task.t,task.n,task.output_max(),if task.direct_sum(){1}else{3});}
        return;
    }
    if args.iter().any(|x|x=="--certify-all") {
        println!("task_id,cartesian_inputs,reachable_scores,maximum_score,output_max,check");
        for task in tasks(){let(_,n,d,m)=certify(&task);println!("{},{n},{d},{m},{},PASS",task.id,task.output_max());}
        return;
    }
    assert!(args.iter().any(|x|x=="--run"), "use --list or --certify-all; encrypted evaluation requires explicit --run");
    let id = arg(&args,"--task"); let task = tasks().into_iter().find(|t|t.id==id).expect("unknown task");
    let parameter = arg(&args,"--parameter"); let manifest = arg(&args,"--manifest");
    let trials = load_trials(&manifest,&task); let (outer,cartesian,reachable,maximum)=certify(&task);
    let (params,budget)=match parameter.as_str(){
        "m1c4" => (PARAM_MESSAGE_1_CARRY_4_KS_PBS,Budget{capacity:32,max_noise:31,message:2}),
        "m2c4" => (PARAM_MESSAGE_2_CARRY_4_KS_PBS,Budget{capacity:64,max_noise:21,message:4}),
        _=>panic!("parameter must be m1c4 or m2c4"),
    };
    assert!(task.t as u64<=budget.message, "fresh inputs must fit message modulus");
    assert!(task.output_max()<budget.message, "output must fit message modulus");
    assert!(maximum<budget.capacity as u64);
    assert!(task.direct_sum() || parameter=="m2c4", "nonbinary packing requires m2c4");
    println!("META,task={},parameter={},message_modulus={},capacity={},max_noise_level={},pbs_base_log={},pbs_level={},lwe_dimension={},polynomial_size={},rayon_threads={}",
        task.id,parameter,budget.message,budget.capacity,budget.max_noise,params.pbs_base_log.0,params.pbs_level.0,params.lwe_dimension.0,params.polynomial_size.0,rayon::current_num_threads());
    println!("META,input=independently_encrypted_symbols,output=one_message_ciphertext,online=checked_packing_inner_PBS_checked_sum_outer_PBS,excluded=keygen_public_tables_encryption_decryption,warmups=5,measured=30,manifest={manifest}");
    println!("CERTIFICATE,cartesian_inputs={cartesian},reachable_scores={reachable},maximum_score={maximum},output_max={}",task.output_max());
    let setup=Instant::now(); let (cks,sks)=gen_keys(params);
    let outer_lut=sks.generate_lookup_table(move |x|outer[x as usize]);
    let inner_luts=if task.direct_sum(){Vec::new()}else{
        (0..task.n/3).map(|_|{
            let task=task.clone(); sks.generate_lookup_table(move |mut x|{
                let mut sum=0;for _ in 0..3{sum+=task.score(x%task.t as u64);x/=task.t as u64;}sum
            })
        }).collect::<Vec<_>>()
    };
    println!("SETUP_MS,{:.6}",setup.elapsed().as_secs_f64()*1000.0);
    println!("phase,index,task_id,inputs,expected,actual,pbs_count,total_ms,outer_degree,outer_noise,output_degree,output_noise,kind");
    for trial in trials{
        let inputs=trial.inputs.iter().map(|&x|cks.encrypt(x)).collect::<Vec<_>>();
        for ct in &inputs{check(ct,budget,"fresh input");}
        reset_pbs_count();let start=Instant::now();
        let transformed=if task.direct_sum(){inputs.clone()}else{
            assert_eq!(task.n%3,0);
            inputs.chunks(3).zip(inner_luts.iter()).map(|(group,lut)|{
                let mut packed=group[0].clone();let mut weight=task.t as u8;
                for ct in &group[1..]{
                    let weighted=sks.checked_scalar_mul(ct,weight).expect("checked packing multiplication rejected");
                    check(&weighted,budget,"weighted input");
                    packed=sks.checked_add(&packed,&weighted).expect("checked packing addition rejected");
                    check(&packed,budget,"packed input");weight*=task.t as u8;
                }
                let y=sks.apply_lookup_table(&packed,lut);check(&y,budget,"inner PBS result");
                assert_eq!(y.noise_level().get(),1);y
            }).collect::<Vec<_>>()
        };
        let sum=checked_sum(&sks,&transformed,budget);let degree=sum.degree.get();let noise=sum.noise_level().get();
        let result=black_box(sks.apply_lookup_table(&sum,&outer_lut));
        check(&result,budget,"outer PBS result");assert!(result.degree.get()<budget.message as usize);assert_eq!(result.noise_level().get(),1);
        let elapsed=start.elapsed().as_secs_f64()*1000.0;let pbs=get_pbs_count();
        let actual=cks.decrypt(&result);assert_eq!(actual,trial.expected);assert_eq!(pbs,if task.direct_sum(){1}else{3});
        let input_text=trial.inputs.iter().map(u64::to_string).collect::<Vec<_>>().join(";");
        println!("{},{},{},{},{},{},{},{:.6},{},{},{},{},{}",trial.phase,trial.index,task.id,input_text,trial.expected,actual,pbs,elapsed,degree,noise,result.degree.get(),result.noise_level().get(),trial.kind);
    }
    println!("COMPLETE,task={},warmups=5,measured=30,mismatches=0",task.id);
}
