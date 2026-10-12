// Round-2 audited t=16 variant; original source is preserved in v1.
use std::env;
use std::process::ExitCode;
use std::time::Instant;

use rayon::prelude::*;
use tfhe::integer::{
    gen_keys_radix, IntegerCiphertext, RadixCiphertext, RadixClientKey, ServerKey,
};
use tfhe::shortint::ciphertext::Degree;
use tfhe::shortint::parameters::PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS;
use tfhe::shortint::server_key::{BivariateLookupTableOwned, LookupTableOwned, ManyLookupTableOwned};
use tfhe::shortint::{
    Ciphertext as ShortintCiphertext, ClientKey as ShortintClientKey,
    ServerKey as ShortintServerKey,
};
use tfhe::{get_pbs_count, reset_pbs_count};

const T: u64 = 16;
const BASE: u64 = 2;
const M_SCALE: u64 = 22;
const LOG_SHIFT: u64 = 1;
const DELTA_OFFSET: u64 = 86;
const RADIX_BASE: u64 = 4;
const RADIX_BLOCKS: usize = 4;
const HIGH_BRANCHES: [u64; 6] = [5, 6, 7, 8, 9, 10];
const RESIDUAL_BRANCHES: usize = 7;

// clog_{2,22}(x) + 1 for x in [0,16).
const CEIL_LOG_SHIFTED: [u64; 16] = [0, 1, 23, 36, 45, 53, 58, 63, 67, 71, 75, 78, 80, 83, 85, 87];

// The public offset is folded into the first transform.  This removes a
// separate radix scalar addition and its carry propagation from the online
// circuit while leaving the shifted difference unchanged.
const CEIL_LOG_WITH_OFFSET: [u64; 16] = [
    86, 87, 109, 122, 131, 139, 144, 149, 153, 157, 161, 164, 166, 169, 171, 173,
];

// floor(22 log_2(x)) + 1 for x in [1,16).  Entry zero is unused.
const FLOOR_LOG_SHIFTED: [u64; 16] = [1, 1, 23, 35, 45, 52, 57, 62, 67, 70, 74, 77, 79, 82, 84, 86];

struct AlgorithmLuts {
    ceil_digits: Vec<LookupTableOwned>,
    floor_digits: Vec<LookupTableOwned>,
    high_base: LookupTableOwned,
    high_equalities: Vec<LookupTableOwned>,
    low_residuals: Vec<LookupTableOwned>,
    gate_residual: BivariateLookupTableOwned,
    partial_sum_refresh: LookupTableOwned,
    final_refresh: LookupTableOwned,
}

struct Evaluation {
    ceil_log_with_offset: RadixCiphertext,
    floor_log_shifted: RadixCiphertext,
    shifted_delta: RadixCiphertext,
    quotient: ShortintCiphertext,
    pbs_count: u64,
    elapsed_ms: f64,
}

#[derive(Clone, Copy)]
enum Selection {
    Default,
    One(u64, u64),
    Count(usize),
    Exhaustive,
    PlaintextOnly,
}

fn make_digit_luts(sks: &ShortintServerKey, table: &'static [u64; 16]) -> Vec<LookupTableOwned> {
    (0..RADIX_BLOCKS)
        .map(|block| {
            sks.generate_lookup_table(move |input| {
                let value = if input < T { table[input as usize] } else { 0 };
                (value / RADIX_BASE.pow(block as u32)) % RADIX_BASE
            })
        })
        .collect()
}

fn apply_digit_luts(
    sks: &ShortintServerKey,
    input: &ShortintCiphertext,
    luts: &[LookupTableOwned],
) -> RadixCiphertext {
    let blocks = luts
        .par_iter()
        .map(|lut| sks.budget_lut(input, lut))
        .collect::<Vec<_>>();
    RadixCiphertext::from(blocks)
}

fn quotient_threshold(quotient_level: usize) -> u64 {
    assert!((1..T as usize).contains(&quotient_level));
    DELTA_OFFSET + CEIL_LOG_SHIFTED[quotient_level] - LOG_SHIFT
}

fn pack_base4_pair(
    sks: &ShortintServerKey,
    low_digit: &ShortintCiphertext,
    high_digit: &ShortintCiphertext,
) -> ShortintCiphertext {
    let mut packed = high_digit.clone();
    sks.budget_scalar_mul_assign(&mut packed, RADIX_BASE as u8);
    sks.budget_add_assign(&mut packed, low_digit);
    packed
}

fn high_base_value(high_nibble: u64) -> u64 {
    match high_nibble {
        0..=5 => 0,
        6 => 1,
        7 => 2,
        8 => 3,
        9 => 6,
        10 => 9,
        _ => 0,
    }
}

fn low_residual(branch: usize, low_nibble: u64) -> u64 {
    let thresholds: &[u64] = match branch {
        0 => &[6],
        1 => &[12],
        2 => &[9],
        3 => &[2, 10, 15],
        4 => &[4, 8, 12],
        5 => &[0, 3, 5],
        6 => &[8, 10, 12],
        _ => unreachable!(),
    };
    thresholds
        .iter()
        .filter(|&&threshold| low_nibble >= threshold)
        .count() as u64
}

fn quotient_from_nibbles(shifted_delta: u64) -> u64 {
    let high = shifted_delta / 16;
    let low = shifted_delta % 16;
    let mut quotient = high_base_value(high);
    match high {
        5..=9 => quotient += low_residual((high - 5) as usize, low),
        10 => quotient += low_residual(5, low) + low_residual(6, low),
        _ => {}
    }
    quotient
}

fn evaluate_algorithm1(
    dividend: u64,
    divisor: u64,
    cks: &RadixClientKey,
    sks: &ServerKey,
    luts: &AlgorithmLuts,
) -> Evaluation {
    assert!(dividend < T);
    assert!((1..T).contains(&divisor));

    let integer_cks: &tfhe::integer::ClientKey = cks.as_ref();
    let shortint_cks: &ShortintClientKey = integer_cks.as_ref();
    let shortint_sks: &ShortintServerKey = sks.as_ref();

    let encrypted_dividend = shortint_cks.unchecked_encrypt(dividend);
    let encrypted_divisor = shortint_cks.unchecked_encrypt(divisor);

    reset_pbs_count();
    let started = Instant::now();

    // The first two GFBP calls of Algorithm 1 are represented by four small
    // base-4 output LUTs each.  Every LUT input is still the encrypted t=16
    // value; no cleartext routing is used.
    let (encrypted_ceil, encrypted_floor) = rayon::join(
        || apply_digit_luts(shortint_sks, &encrypted_dividend, &luts.ceil_digits),
        || apply_digit_luts(shortint_sks, &encrypted_divisor, &luts.floor_digits),
    );

    // Four base-4 blocks represent values modulo 256.  Because the public
    // offset 86 is already included in encrypted_ceil, subtraction directly
    // returns the complete reachable interval [0,172].
    assert_nominal_radix(&encrypted_ceil, "radix subtraction left");
    assert_nominal_radix(&encrypted_floor, "radix subtraction right");
    let shifted_delta = sks.sub_parallelized(&encrypted_ceil, &encrypted_floor);
    assert_nominal_radix(&shifted_delta, "radix subtraction output");

    // Pack the four base-4 digits into low and high nibbles without a PBS.
    // For shifted_delta <= 172 the high nibble is in [0,10].  Each high-nibble
    // row then has at most six low-nibble thresholds, so the outer map can be
    // evaluated with small reusable univariate and bivariate LUTs instead of
    // fifteen four-block radix comparisons.
    let blocks = shifted_delta.blocks();
    let low_nibble = pack_base4_pair(shortint_sks, &blocks[0], &blocks[1]);
    let high_nibble = pack_base4_pair(shortint_sks, &blocks[2], &blocks[3]);

    let ((base, high_equalities), low_residuals) = rayon::join(
        || {
            rayon::join(
                || shortint_sks.budget_lut(&high_nibble, &luts.high_base),
                || {
                    luts.high_equalities
                        .par_iter()
                        .map(|lut| shortint_sks.budget_lut(&high_nibble, lut))
                        .collect::<Vec<_>>()
                },
            )
        },
        || {
            luts.low_residuals
                .par_iter()
                .map(|lut| shortint_sks.budget_lut(&low_nibble, lut))
                .collect::<Vec<_>>()
        },
    );

    let (mut gated_residuals, last_high_extra) = rayon::join(
        || {
            (0..HIGH_BRANCHES.len())
                .into_par_iter()
                .map(|branch| {
                    shortint_sks.budget_bivariate(
                        &high_equalities[branch],
                        &low_residuals[branch],
                        &luts.gate_residual,
                    )
                })
                .collect::<Vec<_>>()
        },
        || {
            shortint_sks.budget_bivariate(
                &high_equalities[5],
                &low_residuals[6],
                &luts.gate_residual,
            )
        },
    );
    gated_residuals.push(last_high_extra);
    assert_eq!(gated_residuals.len(), RESIDUAL_BRANCHES);

    // base + branches H=5,6,7,8 has noise level five and actual range [0,9].
    // One PBS refreshes it.  The remaining mutually exclusive H=9/10 terms
    // have combined actual range [0,6] and noise level three, so they can be
    // added linearly after tightening their proven degree bound.
    let mut first_partial = base;
    for gated in &gated_residuals[..4] {
        shortint_sks.budget_add_assign(&mut first_partial, gated);
    }
    let mut quotient = shortint_sks.budget_lut(&first_partial, &luts.partial_sum_refresh);

    let mut second_partial = gated_residuals[4].clone();
    for gated in &gated_residuals[5..] {
        shortint_sks.budget_add_assign(&mut second_partial, gated);
    }
    second_partial.degree = Degree::new(6);
    shortint_sks.budget_add_assign(&mut quotient, &second_partial);

    // The final linear sum has noise level 4; refresh under the level-5 budget.
    quotient = shortint_sks.budget_lut(&quotient, &luts.final_refresh);
    assert!(quotient.noise_level().get() <= 1 && quotient.degree.get() <= 15);
    let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
    let pbs_count = get_pbs_count();
    Evaluation {
        ceil_log_with_offset: encrypted_ceil,
        floor_log_shifted: encrypted_floor,
        shifted_delta,
        quotient,
        pbs_count,
        elapsed_ms,
    }
}

fn verify_plaintext() -> usize {
    let mut cases = 0;
    for dividend in 0..T {
        for divisor in 1..T {
            let shifted_ceil = CEIL_LOG_SHIFTED[dividend as usize];
            let shifted_floor = FLOOR_LOG_SHIFTED[divisor as usize];
            let signed_delta = shifted_ceil as i64 - shifted_floor as i64;
            let shifted_delta = (signed_delta + DELTA_OFFSET as i64) as u64;
            assert!(shifted_delta <= 172);

            let quotient = (1..T as usize)
                .filter(|&level| shifted_delta >= quotient_threshold(level))
                .count() as u64;
            assert_eq!(quotient_from_nibbles(shifted_delta), quotient);
            assert_eq!(quotient, dividend / divisor);
            cases += 1;
        }
    }
    for shifted_delta in 0..=172 {
        let threshold_quotient = (1..T as usize)
            .filter(|&level| shifted_delta >= quotient_threshold(level))
            .count() as u64;
        assert_eq!(quotient_from_nibbles(shifted_delta), threshold_quotient);
    }
    cases
}

fn deterministic_cases() -> Vec<(u64, u64)> {
    let preferred = [
        (0, 15),
        (1, 1),
        (15, 1),
        (15, 15),
        (6, 13),
        (14, 3),
        (7, 2),
        (8, 3),
        (13, 4),
        (9, 8),
    ];
    let mut cases = preferred.to_vec();
    for dividend in 0..T {
        for divisor in 1..T {
            if !cases.contains(&(dividend, divisor)) {
                cases.push((dividend, divisor));
            }
        }
    }
    cases
}

fn parse_selection() -> Result<Selection, String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Ok(Selection::Default);
    }
    match args[0].as_str() {
        "--plaintext-only" if args.len() == 1 => Ok(Selection::PlaintextOnly),
        "--exhaustive-encrypted" if args.len() == 1 => Ok(Selection::Exhaustive),
        "--samples" if args.len() == 2 => args[1]
            .parse::<usize>()
            .map(Selection::Count)
            .map_err(|_| "--samples requires a positive integer".to_owned()),
        "--case" if args.len() == 3 => {
            let dividend = args[1]
                .parse::<u64>()
                .map_err(|_| "invalid dividend".to_owned())?;
            let divisor = args[2]
                .parse::<u64>()
                .map_err(|_| "invalid divisor".to_owned())?;
            if dividend >= T || !(1..T).contains(&divisor) {
                return Err("valid inputs require 0 <= m < 16 and 1 <= d < 16".to_owned());
            }
            Ok(Selection::One(dividend, divisor))
        }
        _ => Err(
            "usage: section3-algorithm1-reproduction [--plaintext-only | --samples N | --case M D | --exhaustive-encrypted]"
                .to_owned(),
        ),
    }
}

fn run() -> Result<(), String> {
    let selection = parse_selection()?;
    let plaintext_cases = verify_plaintext();
    println!(
        "PLAINTEXT_EXHAUSTIVE_PASS,t={T},M={M_SCALE},base={BASE},cases={plaintext_cases},delta_offset={DELTA_OFFSET}"
    );
    if matches!(selection, Selection::PlaintextOnly) {
        return Ok(());
    }

    println!(
        "ALGORITHM1_CONFIG,t={T},M={M_SCALE},base={BASE},radix_base={RADIX_BASE},intermediate_radix_blocks={RADIX_BLOCKS},quotient_encoding=one_shortint_message_carry_block,parameter=PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,offset_fused=true,parallel_luts=true,outer_route=packed_nibble_piecewise_PBS"
    );
    let key_started = Instant::now();
    let (cks, mut sks) = gen_keys_radix(
        PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,
        RADIX_BLOCKS,
    );
    sks.set_deterministic_pbs_execution(false);
    println!(
        "KEYGEN_MS,{:.6}",
        key_started.elapsed().as_secs_f64() * 1000.0
    );

    let integer_cks: &tfhe::integer::ClientKey = cks.as_ref();
    let shortint_cks: &ShortintClientKey = integer_cks.as_ref();
    let shortint_sks: &ShortintServerKey = sks.as_ref();
    let luts = AlgorithmLuts {
        ceil_digits: make_digit_luts(shortint_sks, &CEIL_LOG_WITH_OFFSET),
        floor_digits: make_digit_luts(shortint_sks, &FLOOR_LOG_SHIFTED),
        high_base: shortint_sks.generate_lookup_table(high_base_value),
        high_equalities: HIGH_BRANCHES
            .iter()
            .copied()
            .map(|high| shortint_sks.generate_lookup_table(move |x| u64::from(x == high)))
            .collect(),
        low_residuals: (0..RESIDUAL_BRANCHES)
            .map(|branch| shortint_sks.generate_lookup_table(move |low| low_residual(branch, low)))
            .collect(),
        gate_residual: shortint_sks
            .generate_lookup_table_bivariate(|condition, residual| condition * residual),
        partial_sum_refresh: shortint_sks.generate_lookup_table(|x| x.min(9)),
        final_refresh: shortint_sks.generate_lookup_table(|value| value),
    };

    println!("DOMAIN,logical_t=8,implementation_t=16,reused_t16_circuit=true");
    let selected=read_protocol_manifest(8)?;
    let measured_count=selected.iter().filter(|x|x.0=="measured").count();

    let mut total_ms = 0.0;
    let mut total_pbs = 0_u64;
    for (phase,index,dividend,divisor) in selected.iter().cloned() {
        let result = evaluate_algorithm1(dividend, divisor, &cks, &sks, &luts);
        let transformed_m_with_offset: u64 = cks.decrypt(&result.ceil_log_with_offset);
        let transformed_m = transformed_m_with_offset - DELTA_OFFSET;
        let transformed_d: u64 = cks.decrypt(&result.floor_log_shifted);
        let shifted_delta: u64 = cks.decrypt(&result.shifted_delta);
        let actual = shortint_cks.decrypt_message_and_carry(&result.quotient);
        let expected = dividend / divisor;
        if transformed_m_with_offset != CEIL_LOG_WITH_OFFSET[dividend as usize]
            || transformed_m != CEIL_LOG_SHIFTED[dividend as usize]
            || transformed_d != FLOOR_LOG_SHIFTED[divisor as usize]
            || shifted_delta != transformed_m_with_offset - transformed_d
            || actual != expected
        {
            return Err(format!(
                "encrypted check failed for {dividend}/{divisor}: transformed_m={transformed_m}, transformed_d={transformed_d}, shifted_delta={shifted_delta}, actual={actual}, expected={expected}"
            ));
        }
        if phase=="measured" {total_ms += result.elapsed_ms; total_pbs += result.pbs_count;}
        println!(
            "ENCRYPTED_RESULT,phase={phase},index={index},m={dividend},d={divisor},clog_plus_1={transformed_m},floorlog_plus_1={transformed_d},shifted_delta={shifted_delta},expected={expected},actual={actual},pbs_count={},elapsed_ms={:.6}",
            result.pbs_count, result.elapsed_ms
        );
    }

    println!(
        "ENCRYPTED_SUMMARY,PASS,cases={},average_pbs={:.3},average_ms={:.6},total_pbs={total_pbs}",
        measured_count,
        total_pbs as f64 / measured_count as f64,
        total_ms / measured_count as f64
    );
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ERROR: {error}");
            ExitCode::FAILURE
        }
    }
}

// Explicit metadata contracts for every hand-composed shortint operation.
// These checks enforce the library's calibrated regime. They are not a
// new proof of Gaussian/FFT tail probabilities or independence assumptions.
trait BudgetChecked {
    fn budget_lut(&self, input: &ShortintCiphertext, lut: &LookupTableOwned) -> ShortintCiphertext;
    fn budget_many(&self, input: &ShortintCiphertext, lut: &ManyLookupTableOwned) -> Vec<ShortintCiphertext>;
    fn budget_bivariate(&self, left: &ShortintCiphertext, right: &ShortintCiphertext, lut: &BivariateLookupTableOwned) -> ShortintCiphertext;
    fn budget_extract(&self, input: &ShortintCiphertext) -> ShortintCiphertext;
    fn budget_add_assign(&self, left: &mut ShortintCiphertext, right: &ShortintCiphertext);
    fn budget_scalar_mul_assign(&self, value: &mut ShortintCiphertext, scalar: u8);
}

fn assert_shortint_budget(value: &ShortintCiphertext, operation: &str) {
    assert!(value.noise_level().get() <= 5,
        "{operation}: noise level {} exceeds calibrated budget 5", value.noise_level().get());
    assert!(value.degree.get() <= 15,
        "{operation}: degree {} exceeds combined capacity 15", value.degree.get());
}

fn assert_nominal_radix(value: &RadixCiphertext, operation: &str) {
    for block in value.blocks() {
        assert!(block.degree.get() <= 3 && block.noise_level().get() <= 1,
            "{operation}: standard radix operation requires carry-free nominal blocks");
    }
}

impl BudgetChecked for ShortintServerKey {
    fn budget_lut(&self, input: &ShortintCiphertext, lut: &LookupTableOwned) -> ShortintCiphertext {
        assert_shortint_budget(input, "univariate PBS input");
        self.apply_lookup_table(input, lut)
    }
    fn budget_many(&self, input: &ShortintCiphertext, lut: &ManyLookupTableOwned) -> Vec<ShortintCiphertext> {
        assert_shortint_budget(input, "many-LUT PBS input");
        assert!(input.degree.get() <= lut.input_max_degree.get(),
            "many-LUT-specific input range exceeded");
        self.apply_many_lookup_table(input, lut)
    }
    fn budget_bivariate(&self, left: &ShortintCiphertext, right: &ShortintCiphertext, lut: &BivariateLookupTableOwned) -> ShortintCiphertext {
        assert_shortint_budget(left, "bivariate left input");
        assert_shortint_budget(right, "bivariate right input");
        self.is_functional_bivariate_pbs_possible(left.noise_degree(), right.noise_degree(), Some(lut))
            .expect("bivariate packing exceeds calibrated budget");
        let mut result = self.unchecked_apply_lookup_table_bivariate(left, right, lut);
        // Every bivariate table in this executable is condition * digit.
        // The table is populated for all 4x4 inputs, but the encrypted condition
        // is a verified bit. Its generic LUT degree 9 is therefore too loose.
        assert!(left.degree.get() <= 1 && right.degree.get() <= 3);
        result.degree = Degree::new(left.degree.get() * right.degree.get());
        result
    }
    fn budget_extract(&self, input: &ShortintCiphertext) -> ShortintCiphertext {
        assert_shortint_budget(input, "radix refresh input");
        self.message_extract(input)
    }
    fn budget_add_assign(&self, left: &mut ShortintCiphertext, right: &ShortintCiphertext) {
        // The integer server key reserves message room in its generic checked
        // max_degree (12). This circuit intentionally uses all 16 combined
        // slots before a PBS, so enforce the actual full-domain bound (15).
        assert!(left.degree.get() + right.degree.get() <= 15,
            "shortint sum exceeds combined-domain degree 15");
        assert!(left.noise_level().get() + right.noise_level().get() <= 5,
            "shortint sum exceeds calibrated noise level 5");
        self.unchecked_add_assign(left, right);
    }
    fn budget_scalar_mul_assign(&self, value: &mut ShortintCiphertext, scalar: u8) {
        assert!(value.degree.get() * scalar as usize <= 15,
            "shortint scalar product exceeds combined-domain degree 15");
        assert!(value.noise_level().get() * scalar as usize <= 5,
            "shortint scalar product exceeds calibrated noise level 5");
        self.unchecked_scalar_mul_assign(value, scalar);
    }
}

fn read_protocol_manifest(t:u64)->Result<Vec<(String,usize,u64,u64)>,String>{
    let path=env::var("DCC_INPUT_MANIFEST").map_err(|_|"DCC_INPUT_MANIFEST is required")?;
    let text=std::fs::read_to_string(&path).map_err(|e|e.to_string())?;
    let mut lines=text.lines();
    if lines.next()!=Some("phase,index,t,m,d,kind"){return Err("bad manifest header".into());}
    let mut result=Vec::new();
    for line in lines {
        let f=line.split(',').collect::<Vec<_>>();
        if f.len()!=6{return Err("bad manifest row".into());}
        let parse=|s:&str|s.parse::<u64>().map_err(|e|e.to_string());
        let row_t=parse(f[2])?;let m=parse(f[3])?;let d=parse(f[4])?;
        if row_t!=t || m>=t || !(1..t).contains(&d){return Err("manifest domain error".into());}
        result.push((f[0].to_owned(),parse(f[1])? as usize,m,d));
    }
    if result.len()!=35 || result.iter().filter(|x|x.0=="warmup").count()!=5 || result.iter().filter(|x|x.0=="measured").count()!=30 {
        return Err("protocol requires 5 warmup and 30 measured rows".into());
    }
    println!("PROTOCOL,manifest={path},warmups=5,measured=30,rayon_threads={}",rayon::current_num_threads());
    Ok(result)
}
