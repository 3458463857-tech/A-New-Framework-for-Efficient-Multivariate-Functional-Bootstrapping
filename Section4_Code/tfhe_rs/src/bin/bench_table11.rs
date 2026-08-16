use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::hint::black_box;
use std::path::Path;
use std::time::Instant;

use tfhe::shortint::parameters::PARAM_MESSAGE_6_CARRY_0_KS_PBS;
use tfhe::shortint::prelude::*;

#[derive(Debug)]
struct Case {
    id: String,
    t: usize,
    ell: usize,
    rows: Vec<Vec<u64>>,
    method: String,
    seed: String,
    iterations: String,
    span: u64,
    distinct_sums: usize,
}

fn load_cases(path: &Path) -> Vec<Case> {
    let text = fs::read_to_string(path).expect("failed to read representation CSV");
    let mut cases: BTreeMap<String, Case> = BTreeMap::new();
    for (line_number, line) in text.lines().enumerate().skip(1) {
        if line.trim().is_empty() {
            continue;
        }
        let fields: Vec<_> = line.split(',').collect();
        assert_eq!(fields.len(), 11, "bad CSV row at line {}", line_number + 1);
        let id = fields[0].to_owned();
        let t: usize = fields[1].parse().expect("bad t");
        let ell: usize = fields[2].parse().expect("bad ell");
        let coordinate: usize = fields[3].parse().expect("bad coordinate");
        let input: usize = fields[4].parse().expect("bad input");
        let score: u64 = fields[5].parse().expect("bad score");
        let span: u64 = fields[9].parse().expect("bad span");
        let distinct_sums: usize = fields[10].parse().expect("bad distinct_sums");
        let case = cases.entry(id.clone()).or_insert_with(|| Case {
            id,
            t,
            ell,
            rows: vec![vec![u64::MAX; t]; ell],
            method: fields[6].to_owned(),
            seed: fields[7].to_owned(),
            iterations: fields[8].to_owned(),
            span,
            distinct_sums,
        });
        assert_eq!((case.t, case.ell, case.span), (t, ell, span));
        assert!(coordinate < ell && input < t);
        case.rows[coordinate][input] = score;
    }
    for case in cases.values() {
        assert!(case.rows.iter().flatten().all(|&value| value != u64::MAX));
    }

    let order = [
        "hamming_weight_interval",
        "symbol_set_interval",
        "symbol_set_threshold",
        "lower_median",
    ];
    order
        .iter()
        .map(|id| cases.remove(*id).unwrap_or_else(|| panic!("missing case {id}")))
        .collect()
}

fn clear_target(case_id: &str, point: &[u64]) -> u64 {
    match case_id {
        "hamming_weight_interval" => {
            let weight = point.iter().copied().sum::<u64>();
            u64::from((4_u64..=6_u64).contains(&weight))
        }
        "symbol_set_interval" => {
            let count = point.iter().filter(|&&value| value == 1 || value == 3).count();
            u64::from((2..=4).contains(&count))
        }
        "symbol_set_threshold" => {
            let count = point.iter().filter(|&&value| value == 0 || value == 2).count();
            u64::from(count >= 3)
        }
        "lower_median" => {
            let mut ordered = point.to_vec();
            ordered.sort_unstable();
            ordered[(ordered.len() - 1) / 2]
        }
        _ => panic!("unknown case {case_id}"),
    }
}

fn enumerate_points<F: FnMut(&[u64])>(t: usize, point: &mut [u64], index: usize, f: &mut F) {
    if index == point.len() {
        f(point);
        return;
    }
    for value in 0..t as u64 {
        point[index] = value;
        enumerate_points(t, point, index + 1, f);
    }
}

fn verified_outer_table(case: &Case) -> Vec<u64> {
    let mut outer = vec![u64::MAX; 64];
    let mut point = vec![0_u64; case.ell];
    let mut seen = 0_usize;
    enumerate_points(case.t, &mut point, 0, &mut |values| {
        let sum: u64 = values
            .iter()
            .enumerate()
            .map(|(coordinate, &value)| case.rows[coordinate][value as usize])
            .sum();
        assert!(sum < 64, "representation exceeds the selected message modulus");
        let output = clear_target(&case.id, values);
        let slot = &mut outer[sum as usize];
        if *slot == u64::MAX {
            *slot = output;
            seen += 1;
        } else {
            assert_eq!(*slot, output, "representation collision for {}", case.id);
        }
    });
    assert_eq!(seen, case.distinct_sums);
    let reachable_max = outer
        .iter()
        .enumerate()
        .filter(|(_, value)| **value != u64::MAX)
        .map(|(index, _)| index)
        .max()
        .expect("empty outer table") as u64;
    assert_eq!(reachable_max, case.span);
    for value in &mut outer {
        if *value == u64::MAX {
            *value = 0;
        }
    }
    outer
}

fn next_random(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

fn percentile(sorted: &[f64], fraction: f64) -> f64 {
    let index = ((sorted.len() - 1) as f64 * fraction).round() as usize;
    sorted[index]
}

fn main() {
    let records_path = env::args()
        .nth(1)
        .unwrap_or_else(|| "../chapter4_compression/records/table11_representations.csv".into());
    let repetitions: usize = env::args()
        .nth(2)
        .and_then(|value| value.parse().ok())
        .unwrap_or(30);
    assert!(repetitions >= 3);

    let cases = load_cases(Path::new(&records_path));
    // The six message bits represent [64].  For t <= 4, three variables can
    // be packed as x_0 + t*x_1 + t^2*x_2 < 64.  One packed inner LUT returns
    // p_0(x_0)+p_1(x_1)+p_2(x_2), exactly as described in Section 4.  Thus the
    // three non-binary cases use two packed inner PBS calls and one outer PBS.
    let (client_key, server_key) = gen_keys(PARAM_MESSAGE_6_CARRY_0_KS_PBS);
    println!("TABLE11_ENV,tfhe_rs=0.8.7,parameter=PARAM_MESSAGE_6_CARRY_0_KS_PBS,packing=base_t_groups_of_3,repetitions={repetitions}");

    for (case_index, case) in cases.iter().enumerate() {
        let outer_values = verified_outer_table(case);
        let outer_lut = server_key.generate_lookup_table(move |value| outer_values[value as usize]);
        let skip_inner_pbs = case.id == "hamming_weight_interval";
        let packed_inner_luts: Vec<_> = if skip_inner_pbs {
            Vec::new()
        } else {
            case.rows
                .chunks(3)
                .map(|rows| {
                    let rows = rows.to_vec();
                    let radix = case.t as u64;
                    server_key.generate_lookup_table(move |mut packed| {
                        rows.iter()
                            .map(|row| {
                                let digit = (packed % radix) as usize;
                                packed /= radix;
                                row[digit]
                            })
                            .sum()
                    })
                })
                .collect()
        };
        let pbs_calls = if skip_inner_pbs {
            1
        } else {
            packed_inner_luts.len() + 1
        };
        assert_eq!(pbs_calls, if skip_inner_pbs { 1 } else { 3 });
        println!(
            "TABLE11_PACKING,{},group_size=3,packed_inner_calls={},outer_calls=1,total_calls={}",
            case.id,
            packed_inner_luts.len(),
            pbs_calls
        );

        let run_once = |ciphertexts: &[Ciphertext]| {
            let transformed: Vec<_> = if skip_inner_pbs {
                ciphertexts.to_vec()
            } else {
                ciphertexts
                    .chunks(3)
                    .zip(packed_inner_luts.iter())
                    .map(|(group, lut)| {
                        let mut packed = group[0].clone();
                        let mut radix = case.t as u8;
                        for ciphertext in group.iter().skip(1) {
                            let weighted = server_key.unchecked_scalar_mul(ciphertext, radix);
                            packed = server_key.unchecked_add(&packed, &weighted);
                            radix *= case.t as u8;
                        }
                        server_key.apply_lookup_table(&packed, lut)
                    })
                    .collect()
            };
            let mut accumulator = transformed[0].clone();
            for ciphertext in transformed.iter().skip(1) {
                accumulator = server_key.unchecked_add(&accumulator, ciphertext);
            }
            server_key.apply_lookup_table(&accumulator, &outer_lut)
        };

        let warmup_inputs: Vec<_> = (0..case.ell).map(|index| (index % case.t) as u64).collect();
        let warmup_ciphertexts: Vec<_> = warmup_inputs
            .iter()
            .map(|&value| client_key.encrypt(value))
            .collect();
        for _ in 0..5 {
            let output = black_box(run_once(&warmup_ciphertexts));
            let actual: u64 = client_key.decrypt(&output);
            assert_eq!(actual, clear_target(&case.id, &warmup_inputs));
        }

        let mut random_state = 0x2026_0810_5a17_0001_u64 ^ case_index as u64;
        let mut times = Vec::with_capacity(repetitions);
        for repetition in 0..repetitions {
            let inputs: Vec<_> = (0..case.ell)
                .map(|_| (next_random(&mut random_state) % case.t as u64) as u64)
                .collect();
            let ciphertexts: Vec<_> = inputs
                .iter()
                .map(|&value| client_key.encrypt(value))
                .collect();
            let start = Instant::now();
            let output = black_box(run_once(&ciphertexts));
            let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
            let actual: u64 = client_key.decrypt(&output);
            let expected = clear_target(&case.id, &inputs);
            assert_eq!(actual, expected, "encrypted output mismatch for {}", case.id);
            times.push(elapsed_ms);
            let input_text = inputs.iter().map(u64::to_string).collect::<Vec<_>>().join(":");
            println!(
                "TABLE11_RESULT,{},{},{},{},{:.6}",
                case.id, repetition, input_text, actual, elapsed_ms
            );
        }

        let average = times.iter().sum::<f64>() / times.len() as f64;
        let variance = times
            .iter()
            .map(|value| (value - average) * (value - average))
            .sum::<f64>()
            / times.len() as f64;
        let mut sorted = times.clone();
        sorted.sort_by(f64::total_cmp);
        println!(
            "TABLE11_SUMMARY,{},{},{},{},{},{},{},{:.6},{:.6},{:.6},{:.6},{:.6}",
            case.id,
            case.t,
            case.ell,
            pbs_calls,
            case.span,
            case.method,
            case.seed,
            average,
            variance.sqrt(),
            percentile(&sorted, 0.5),
            sorted[0],
            sorted[sorted.len() - 1],
        );
        if !case.iterations.is_empty() {
            println!("TABLE11_SEARCH,{},iterations={}", case.id, case.iterations);
        }
    }
}
