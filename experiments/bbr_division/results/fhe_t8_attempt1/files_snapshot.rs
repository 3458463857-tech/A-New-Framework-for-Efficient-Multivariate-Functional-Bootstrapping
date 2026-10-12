use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{self, BufRead, BufReader, Error, Read};
use std::path::PathBuf;
use tfhe::gadget::prelude::*;

use csv::ReaderBuilder;

pub fn read_parameters_decompositions(filename: &PathBuf) -> (usize, Vec<usize>, usize) {
    // Open the file
    let mut file = File::open(filename).unwrap();

    // Read the file content into a string
    let mut content = String::new();
    let _ = file.read_to_string(&mut content);

    // Regex to parse the file lines
    let l_re = Regex::new(r"l=(\d+)").unwrap();
    let t_is_re = Regex::new(r"t_is=\[([0-9, ]+)\]").unwrap();
    let nu_re = Regex::new(r"nu=(\d+)").unwrap();

    // Extract data using regex
    let l = l_re.captures(&content).unwrap()[1]
        .parse::<usize>()
        .unwrap();

    let t_is = t_is_re.captures(&content).unwrap()[1]
        .split(", ")
        .map(|s| s.parse::<usize>().unwrap())
        .collect::<Vec<_>>();

    let nu = nu_re.captures(&content).unwrap()[1]
        .parse::<usize>()
        .unwrap();

    (l, t_is, nu)
}

pub fn import_parameters_from_table(p: u64, nu: usize, perror: usize) -> Option<BooleanParameters> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(format!("../../parameters/optimizer_cjp_odd-{}.csv", perror));

    // Open the file
    let file = File::open(path).ok()?;

    // Create a CSV reader with headers enabled
    let mut rdr = ReaderBuilder::new()
        .has_headers(true) // This ensures the first row is treated as headers
        .from_reader(file);

    // Iterate over each record
    for result in rdr.records() {
        let record = result.unwrap();
        let nu_record = record[1].parse::<usize>().unwrap();
            if record[0].parse::<u64>().unwrap() == p && nu <= nu_record {
                println!("{:?}", record);
            return Some(BooleanParameters {
                lwe_dimension: LweDimension(record[6].parse().unwrap()),
                glwe_dimension: GlweDimension(record[4].parse().unwrap()),
                polynomial_size: PolynomialSize(record[5].parse().unwrap()),
                lwe_modular_std_dev: StandardDev(record[9].parse().unwrap()),
                glwe_modular_std_dev: StandardDev(record[10].parse().unwrap()),
                pbs_base_log: DecompositionBaseLog(
                    record[8]
                        .parse::<usize>()
                        .unwrap()
                        .ilog2()
                        .try_into()
                        .unwrap(),
                ),
                pbs_level: DecompositionLevelCount(record[3].parse().unwrap()),
                ks_base_log: DecompositionBaseLog(
                    record[7]
                        .parse::<usize>()
                        .unwrap()
                        .ilog2()
                        .try_into()
                        .unwrap(),
                ),
                ks_level: DecompositionLevelCount(record[2].parse().unwrap()),
                encryption_key_choice: EncryptionKeyChoice::Big,
            });
        }
    }
    None
}

pub fn read_gammas(filename: &PathBuf) -> io::Result<Vec<Vec<u64>>> {
    read_betas(filename)
}

pub fn read_betas(filename: &PathBuf) -> io::Result<Vec<Vec<u64>>> {
    // Open the file
    let file = File::open(filename)?;
    let reader = BufReader::new(file);

    // Read the first line
    let lines = reader.lines();

    Ok(lines
        .map(|line| {
            line.unwrap()
                .split_whitespace()
                .map(|s| s.parse::<u64>().expect("parse error"))
                .collect()
        })
        .collect())
}

pub fn read_sbox(filename: &PathBuf) -> io::Result<Vec<u64>> {
    let file = File::open(filename)?;
    let reader = BufReader::new(file);
    let mut lines = reader.lines();

    Ok(lines
        .next()
        .unwrap()
        .unwrap()
        .split_whitespace()
        .map(|s| s.parse::<u64>().expect("parse error"))
        .collect())
}

pub fn read_encodings(filename: &PathBuf, s: u64, p: u64) -> Vec<Encoding> {
    let mut encodings = vec![];
    let mut current = None;

    let file = File::open(filename).unwrap();
    let reader = BufReader::new(file);
    let lines = reader.lines();

    let mut counter = 0;
    for (line_number, raw_line) in lines.enumerate() {
        let line = raw_line.unwrap();
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Some(_) = line.strip_prefix("Decomposition ") {
            if let Some(prev) = current.take() {
                encodings.push(Encoding::new(s, prev, p));
                counter += 1;
            }
            current = Some(vec![]);
            continue;
        }

        let (lhs, rhs) = line
            .split_once(':')
            .ok_or_else(|| format!("line {}: expected `key : values`", line_number))
            .unwrap();

        let key = lhs
            .trim()
            .parse::<usize>()
            .map_err(|_| format!("line {}: invalid key", line_number))
            .unwrap();

        let values = rhs
            .split_whitespace()
            .map(|s| {
                s.parse::<u64>()
                    .map_err(|_| format!("line {}: invalid value `{}`", line_number, s))
            })
            .collect::<Result<HashSet<_>, _>>()
            .unwrap();

        let dec = current
            .as_mut()
            .ok_or_else(|| {
                format!(
                    "line {}: entry before any decomposition header",
                    line_number
                )
            })
            .unwrap();

        dec.push(values);
    }

    if let Some(prev) = current.take() {
        encodings.push(Encoding::new(s, prev, p));
    }

    encodings
}

pub fn read_phis_from_file(
    filename: &PathBuf,
) -> io::Result<HashMap<(i64, usize), (Vec<u64>, Vec<u64>)>> {
    let file = File::open(filename)?;
    let mut lines = BufReader::new(file).lines();
    let mut phis = HashMap::new();
    let mut current_chain = -1;
    let mut current_index = 0;
    let mut first_vector = Vec::new();

    assert_eq!(lines.next().unwrap()?, "Base:");

    for line in lines {
        let line = line?;
        if line.starts_with("Chain") {
            // Extract the key
            current_chain = line
                .trim_start_matches("Chain ")
                .trim_end_matches(':')
                .parse()
                .expect("parse error");
        } else if line.ends_with(':') {
            current_index = line.trim_end_matches(':').parse().expect("parse error");
        } else if !line.is_empty() {
            // Split the line into a vector of integers
            let vector: Vec<u64> = line
                .split_whitespace()
                .map(|s| s.parse().expect("parse error"))
                .collect();
            if first_vector.is_empty() {
                first_vector = vector;
            } else {
                phis.insert(
                    (current_chain, current_index),
                    (first_vector.clone(), vector),
                );
                first_vector.clear();
            }
        }
    }

    Ok(phis)
}
