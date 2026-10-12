use std::{collections::HashMap, error::Error, fs::File, io::Write, time::Instant};

use clap::Parser;
use decomposition::Decomposition;
use serde::{Deserialize, Serialize};
use tfhe::gadget::prelude::*;

use crate::cli::{mode_string, Cli, Cmd, Mode};

pub mod cli;
pub mod decomposition;
pub mod files;

fn perf_measurement(
    s_log: usize,
    p: u64,
    n: usize,
    m: usize,
    n_tests: usize,
    perror: usize,
    mode: &str,
) -> u128 {
    assert!(m <= n);

    let s = 1 << s_log;
    let decomposition = Decomposition::load_decomposition(s_log, p, n, perror, mode);

    let (client_key, server_key) = gen_keys(&decomposition.parameters);

    let input_encoding = Encoding::new_trivial(p);

    let mut durations = vec![];

    for input in 0..n_tests {
        println!("input: {}", input);
        let input_s_box: Vec<u64> = (0..n)
            .map(|i| ((input >> (i * s_log)) % s) as u64)
            .collect();

        let x_ins: Vec<Ciphertext> = input_s_box
            .iter()
            .map(|m| client_key.encrypt_arithmetic(*m, &input_encoding))
            .collect();

        let start = Instant::now();
        decomposition.partial_lut_evaluation(&x_ins, &server_key, m, &client_key);
        let stop = start.elapsed();
        durations.push(stop.as_millis());
    }
    durations.into_iter().sum::<u128>() / n_tests as u128
}

#[derive(Serialize, Deserialize, Debug)]
struct ResultsHolderFullEValuation {
    map: HashMap<String, HashMap<String, u128>>,
}

fn compute_all_timings_full_evaluation(perror: usize, mode: &str) -> Result<(), Box<dyn Error>> {
    let mut map_timings = HashMap::new();
    map_timings.insert("3".to_string(), HashMap::new());
    map_timings.insert("5".to_string(), HashMap::new());
    map_timings.insert("17".to_string(), HashMap::new());

    let s_log = 1;
    let p = 3;
    for n in 4..15 {
        println!("p={};n={}", p, n);
        map_timings.get_mut("3").unwrap().insert(
            n.to_string(),
            perf_measurement(s_log, p, n, n, 5, perror, mode),
        );
    }

    let s_log = 2;
    let p = 5;
    for n in 2..8 {
        println!("p={};n={}", p, n);
        map_timings.get_mut("5").unwrap().insert(
            n.to_string(),
            perf_measurement(s_log, p, n, n, 5, perror, mode),
        );
    }

    let s_log = 4;
    let p = 17;
    for n in 2..4 {
        println!("p={};n={}", p, n);
        map_timings.get_mut("17").unwrap().insert(
            n.to_string(),
            perf_measurement(s_log, p, n, n, 5, perror, mode),
        );
    }


    let data_timings = ResultsHolderFullEValuation { map: map_timings };

    let json_timings = serde_json::to_string_pretty(&data_timings.map)?;
    // Write the JSON string to a file
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(format!("../../data/regenerated/timings_hlut-{}.json", perror));

    let mut file = File::create(path)?;
    file.write_all(json_timings.as_bytes())?;
    Ok(())
}

#[derive(Serialize, Deserialize, Debug)]
struct ResultsHolderPartialEvaluation {
    map: HashMap<String, HashMap<String, HashMap<String, u128>>>,
}

fn compute_all_timings_partial_evaluation(perror: usize, mode: &str) -> Result<(), Box<dyn Error>> {
    let mut map_timings = HashMap::new();
    map_timings.insert("3".to_string(), HashMap::new());
    map_timings.insert("5".to_string(), HashMap::new());
    map_timings.insert("17".to_string(), HashMap::new());

    let s_log = 1;
    let p = 3;
    for n in 4..15 {
        println!("p={};n={}", p, n);
        map_timings
            .get_mut("3")
            .unwrap()
            .insert(n.to_string(), HashMap::new());
        for m in 1..=n {
            println!("\tm={m}");
            map_timings
                .get_mut("3")
                .unwrap()
                .get_mut(&n.to_string())
                .unwrap()
                .insert(
                    m.to_string(),
                    perf_measurement(s_log, p, n, m, 5, perror, mode),
                );
        }
    }

    let s_log = 2;
    let p = 5;
    for n in 2..8 {
        println!("p={};n={}", p, n);
        map_timings
            .get_mut("5")
            .unwrap()
            .insert(n.to_string(), HashMap::new());
        for m in 1..=n {
            println!("\tm={m}");
            map_timings
                .get_mut("5")
                .unwrap()
                .get_mut(&n.to_string())
                .unwrap()
                .insert(
                    m.to_string(),
                    perf_measurement(s_log, p, n, m, 5, perror, mode),
                );
        }
    }

    let s_log = 4;
    let p = 17;
    for n in 2..4 {
        println!("p={};n={}", p, n);
        map_timings
            .get_mut("17")
            .unwrap()
            .insert(n.to_string(), HashMap::new());
        for m in 1..=n {
            println!("\tm={m}");
            map_timings
                .get_mut("17")
                .unwrap()
                .get_mut(&n.to_string())
                .unwrap()
                .insert(
                    m.to_string(),
                    perf_measurement(s_log, p, n, m, 5, perror, mode),
                );
        }
    }

    let data_timings = ResultsHolderPartialEvaluation { map: map_timings };

    let json_timings = serde_json::to_string_pretty(&data_timings.map)?;

    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(format!(
        "../../data/regenerated/timings_hlut_partial_evaluations-{}.json",
         perror
    ));

    let mut file = File::create(path)?;
    file.write_all(json_timings.as_bytes())?;
    Ok(())
}

fn main() {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Full(opts) => {
            if opts.perror == 40 || opts.perror == 128 {
                compute_all_timings_full_evaluation(opts.perror, &mode_string(opts.mode))
            } else {
                panic!("Only perror allowed are 40 and 128");
            }
        }

        Cmd::Partial(opts) => {
            if opts.perror == 40 || opts.perror == 128 {
                compute_all_timings_partial_evaluation(opts.perror, &mode_string(opts.mode))
            } else {
                panic!("Only perror allowed are 40 and 128");
            }
        }
    }
    .unwrap()
}
