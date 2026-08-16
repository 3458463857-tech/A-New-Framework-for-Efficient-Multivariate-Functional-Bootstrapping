use std::collections::BTreeMap;
use std::env;
use std::process::ExitCode;
use std::time::Instant;

use rayon::prelude::*;
use tfhe::integer::{
    gen_keys_radix, IntegerCiphertext, RadixCiphertext, RadixClientKey, ServerKey,
};
use tfhe::shortint::ciphertext::Degree;
use tfhe::shortint::parameters::PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS;
use tfhe::shortint::server_key::{
    BivariateLookupTableOwned, LookupTableOwned, ManyLookupTableOwned,
};
use tfhe::shortint::{
    Ciphertext as ShortintCiphertext, ClientKey as ShortintClientKey,
    ServerKey as ShortintServerKey,
};
use tfhe::{get_pbs_count, reset_pbs_count};

const BASE: u64 = 2;
const INPUT_CHUNK: u64 = 16;
const RADIX_BASE: u64 = 4;
const QUOTIENT_RADIX_BLOCKS: usize = 3;
const OUTER_CHUNK: u64 = 16;

struct OuterResidualGroup {
    high: u64,
    mids: Vec<u64>,
    mid_selector: usize,
    residual_values: Vec<u64>,
    max_residual: u64,
}

struct OuterResidual {
    group: usize,
    component: usize,
}

enum BranchDigitLut {
    Zero,
    Constant(u64),
    Variable(LookupTableOwned),
}

struct Config {
    t: u64,
    m_scale: u64,
    radix_blocks: usize,
    input_branches: usize,
    delta_offset: u64,
    max_shifted_delta: u64,
    ceil_shifted: Vec<u64>,
    floor_shifted: Vec<u64>,
    ceil_with_offset: Vec<u64>,
    thresholds: Vec<u64>,
    outer_base_values: Vec<u64>,
    outer_highs: Vec<u64>,
    outer_mid_selectors: Vec<Vec<u64>>,
    outer_groups: Vec<OuterResidualGroup>,
    outer_residuals: Vec<OuterResidual>,
    residual_bins: Vec<Vec<usize>>,
    max_row_residual: u64,
}

struct AlgorithmLuts {
    equalities: Vec<LookupTableOwned>,
    equalities_many: Option<ManyLookupTableOwned>,
    ceil_branch_digits: Vec<BranchDigitLut>,
    floor_branch_digits: Vec<BranchDigitLut>,
    gate_digit: BivariateLookupTableOwned,
    outer_high_equalities: Vec<LookupTableOwned>,
    outer_high_equalities_many: Option<ManyLookupTableOwned>,
    outer_mid_equalities: Vec<LookupTableOwned>,
    outer_base_digits: Vec<BranchDigitLut>,
    outer_residual_digits: Vec<LookupTableOwned>,
    one_hot_refresh: LookupTableOwned,
    residual_split_digits: Vec<LookupTableOwned>,
    residual_split_digits_many: Option<ManyLookupTableOwned>,
}

struct Evaluation {
    ceil_log_with_offset: RadixCiphertext,
    floor_log_shifted: RadixCiphertext,
    shifted_delta: RadixCiphertext,
    quotient: RadixCiphertext,
    pbs_count: u64,
    elapsed_ms: f64,
    input_pbs: u64,
    subtraction_pbs: u64,
    outer_pbs: u64,
    input_ms: f64,
    subtraction_ms: f64,
    outer_ms: f64,
}

#[derive(Clone, Copy)]
enum Selection {
    Default,
    One(u64, u64),
    Count(usize),
    Exhaustive,
    PlaintextOnly,
}

#[derive(Clone, Copy)]
enum OuterRoute {
    Packed,
    Threshold,
}

fn shifted_ceil(value: u64, scale: u64) -> u64 {
    if value == 0 {
        0
    } else {
        (scale as f64 * (value as f64).log2()).ceil() as u64 + 1
    }
}

fn shifted_floor(value: u64, scale: u64) -> u64 {
    (scale as f64 * (value as f64).log2()).floor() as u64 + 1
}

fn make_config(t: u64) -> Result<Config, String> {
    let (m_scale, radix_blocks) = match t {
        32 => (44, 5),
        64 => (89, 6),
        _ => return Err("the small-parameter runner supports only --t 32 or --t 64".into()),
    };
    let ceil_shifted = (0..t)
        .map(|value| shifted_ceil(value, m_scale))
        .collect::<Vec<_>>();
    let floor_shifted = (0..t)
        .map(|value| {
            if value == 0 {
                1
            } else {
                shifted_floor(value, m_scale)
            }
        })
        .collect::<Vec<_>>();
    let delta_offset = *floor_shifted[1..]
        .iter()
        .max()
        .expect("the divisor domain is nonempty");
    let ceil_with_offset = ceil_shifted
        .iter()
        .map(|value| value + delta_offset)
        .collect::<Vec<_>>();
    let thresholds = (1..t as usize)
        .map(|level| delta_offset + ceil_shifted[level] - 1)
        .collect::<Vec<_>>();
    let max_shifted_delta = delta_offset + ceil_shifted[t as usize - 1] - 1;
    assert!(max_shifted_delta < RADIX_BASE.pow(radix_blocks as u32));
    let grouped_rows: &[&[u64]] = match t {
        32 => &[
            &[13],
            &[16],
            &[19, 27],
            &[20],
            &[21, 25],
            &[22, 24],
            &[23, 26],
        ],
        64 => &[
            &[33],
            &[38],
            &[42],
            &[44],
            &[46],
            &[47],
            &[51],
            &[53],
            &[48, 50],
            &[49],
            &[54, 56, 55],
            &[57, 58, 59],
            &[52, 61],
            &[60, 62, 63],
            &[64, 65],
            &[66],
        ],
        _ => unreachable!(),
    };
    let last_outer_row = max_shifted_delta / OUTER_CHUNK;
    let mut outer_base_values = (0..=last_outer_row)
        .map(|row| {
            thresholds
                .iter()
                .filter(|&&threshold| threshold <= row * OUTER_CHUNK)
                .count() as u64
        })
        .collect::<Vec<_>>();
    if t == 32 {
        for (row, base) in [
            (16, 1),
            (19, 3),
            (20, 5),
            (21, 4),
            (22, 7),
            (23, 10),
            (24, 13),
            (25, 18),
            (26, 23),
            (27, 29),
        ] {
            outer_base_values[row] = base;
        }
    } else if t == 64 {
        for (row, base) in [
            (33, 0),
            (38, 1),
            (42, 2),
            (44, 3),
            (46, 4),
            (47, 5),
            (48, 6),
            (49, 7),
            (50, 8),
            (51, 9),
            (52, 9),
            (53, 11),
            (54, 13),
            (55, 15),
            (56, 17),
            (57, 19),
            (58, 22),
            (59, 25),
            (60, 27),
            (61, 32),
            (62, 36),
            (63, 41),
            (64, 46),
            (65, 52),
            (66, 59),
        ] {
            outer_base_values[row] = base;
        }
    }
    let mut reachable_rows = BTreeMap::<u64, BTreeMap<u64, u64>>::new();
    for dividend in 0..t {
        for divisor in 1..t {
            let shifted_delta = ceil_shifted[dividend as usize] + delta_offset
                - floor_shifted[divisor as usize];
            let row = shifted_delta / OUTER_CHUNK;
            let low = shifted_delta % OUTER_CHUNK;
            let residual = dividend / divisor - outer_base_values[row as usize];
            let old = reachable_rows.entry(row).or_default().insert(low, residual);
            assert!(old.is_none_or(|value| value == residual));
        }
    }
    let mut outer_groups = grouped_rows
        .iter()
        .map(|rows| {
            let high = rows[0] / OUTER_CHUNK;
            let mut assigned = [None; OUTER_CHUNK as usize];
            for &row in *rows {
                assert_eq!(row / OUTER_CHUNK, high);
                for (&low, &residual) in &reachable_rows[&row] {
                    let slot = &mut assigned[low as usize];
                    assert!(slot.is_none_or(|value| value == residual));
                    *slot = Some(residual);
                }
            }
            let residual_values = assigned
                .into_iter()
                .map(|value| value.unwrap_or(0))
                .collect::<Vec<_>>();
            let max_residual = *residual_values.iter().max().unwrap();
            assert!(max_residual > 0);
            OuterResidualGroup {
                high,
                mids: {
                    let mut mids = rows
                        .iter()
                        .map(|row| row % OUTER_CHUNK)
                        .collect::<Vec<_>>();
                    mids.sort_unstable();
                    mids
                },
                mid_selector: 0,
                residual_values,
                max_residual,
            }
        })
        .collect::<Vec<_>>();
    let mut outer_mid_selectors = Vec::<Vec<u64>>::new();
    for group in &mut outer_groups {
        group.mid_selector = if let Some(index) = outer_mid_selectors
            .iter()
            .position(|mids| mids == &group.mids)
        {
            index
        } else {
            outer_mid_selectors.push(group.mids.clone());
            outer_mid_selectors.len() - 1
        };
    }
    let outer_residuals = outer_groups
        .iter()
        .enumerate()
        .flat_map(|(group, outer_group)| {
            (0..outer_group
                .max_residual
                .div_ceil(RADIX_BASE - 1) as usize)
                .map(move |component| OuterResidual { group, component })
        })
        .collect::<Vec<_>>();
    let max_row_residual = outer_groups
        .iter()
        .map(|group| group.max_residual)
        .max()
        .expect("the outer table has at least one nonconstant row");
    let residual_bins = pack_residual_groups(&outer_groups);
    let first_outer_high = outer_groups
        .first()
        .expect("the outer table has at least one nonconstant row")
        .high;
    let last_outer_high = max_shifted_delta / (OUTER_CHUNK * OUTER_CHUNK);
    let outer_highs = (first_outer_high..=last_outer_high).collect::<Vec<_>>();
    Ok(Config {
        t,
        m_scale,
        radix_blocks,
        input_branches: (t / INPUT_CHUNK) as usize,
        delta_offset,
        max_shifted_delta,
        ceil_shifted,
        floor_shifted,
        ceil_with_offset,
        thresholds,
        outer_base_values,
        outer_highs,
        outer_mid_selectors,
        outer_groups,
        outer_residuals,
        residual_bins,
        max_row_residual,
    })
}

fn pack_residual_groups(groups: &[OuterResidualGroup]) -> Vec<Vec<usize>> {
    let mut group_indices = (0..groups.len()).collect::<Vec<_>>();
    group_indices.sort_by_key(|&group| std::cmp::Reverse(groups[group].max_residual));
    let mut bins = Vec::<(usize, usize, Vec<usize>)>::new();
    for group in group_indices {
        let degree = groups[group].max_residual as usize;
        let noise = degree.div_ceil((RADIX_BASE - 1) as usize);
        if let Some((used_degree, used_noise, indices)) =
            bins.iter_mut().find(|(used_degree, used_noise, _)| {
                *used_degree + degree <= 15 && *used_noise + noise <= 5
            })
        {
            *used_degree += degree;
            *used_noise += noise;
            indices.push(group);
        } else {
            bins.push((degree, noise, vec![group]));
        }
    }
    bins.into_iter().map(|(_, _, rows)| rows).collect()
}

fn make_branch_digit_luts(
    config: &Config,
    sks: &ShortintServerKey,
    table: &[u64],
) -> Vec<BranchDigitLut> {
    (0..config.input_branches)
        .flat_map(|branch| {
            (0..config.radix_blocks)
                .map(move |block| (branch, block))
                .collect::<Vec<_>>()
        })
        .map(|(branch, block)| {
            let digit_values = (0..INPUT_CHUNK)
                .map(|low| {
                    let input = branch as u64 * INPUT_CHUNK + low;
                    (table[input as usize] / RADIX_BASE.pow(block as u32)) % RADIX_BASE
                })
                .collect::<Vec<_>>();
            if digit_values.iter().all(|&value| value == 0) {
                BranchDigitLut::Zero
            } else if digit_values
                .iter()
                .all(|&value| value == digit_values[0])
            {
                BranchDigitLut::Constant(digit_values[0])
            } else {
                BranchDigitLut::Variable(
                    sks.generate_lookup_table(move |low| digit_values[low as usize]),
                )
            }
        })
        .collect()
}

fn make_many_equalities(sks: &ShortintServerKey, expected_values: &[u64]) -> ManyLookupTableOwned {
    let functions = expected_values
        .iter()
        .copied()
        .map(|expected| {
            Box::new(move |value| u64::from(value == expected)) as Box<dyn Fn(u64) -> u64>
        })
        .collect::<Vec<_>>();
    let references = functions
        .iter()
        .map(|function| function.as_ref() as &dyn Fn(u64) -> u64)
        .collect::<Vec<_>>();
    sks.generate_many_lookup_table(&references)
}

fn make_luts(config: &Config, sks: &ShortintServerKey) -> AlgorithmLuts {
    let outer_base_digits = config
        .outer_highs
        .iter()
        .copied()
        .flat_map(|high| {
            (0..QUOTIENT_RADIX_BLOCKS)
                .map(move |digit| (high, digit))
                .collect::<Vec<_>>()
        })
        .map(|(high, digit)| {
            let base_values = config.outer_base_values.clone();
            let digit_values = (0..OUTER_CHUNK)
                .map(|mid| {
                    let row = high * OUTER_CHUNK + mid;
                    let base = base_values.get(row as usize).copied().unwrap_or(0);
                    (base / RADIX_BASE.pow(digit as u32)) % RADIX_BASE
                })
                .collect::<Vec<_>>();
            if digit_values.iter().all(|&value| value == 0) {
                BranchDigitLut::Zero
            } else if digit_values
                .iter()
                .all(|&value| value == digit_values[0])
            {
                BranchDigitLut::Constant(digit_values[0])
            } else {
                BranchDigitLut::Variable(
                    sks.generate_lookup_table(move |mid| digit_values[mid as usize]),
                )
            }
        })
        .collect();
    let outer_residual_digits = config
        .outer_residuals
        .iter()
        .map(|residual| {
            (
                config.outer_groups[residual.group].residual_values.clone(),
                residual.component,
            )
        })
        .map(|(residual_values, component)| {
            sks.generate_lookup_table(move |low| {
                residual_values[low as usize]
                    .saturating_sub(component as u64 * (RADIX_BASE - 1))
                    .min(RADIX_BASE - 1)
            })
        })
        .collect();
    AlgorithmLuts {
        equalities: if config.input_branches == 2 {
            vec![sks.generate_lookup_table(|high| u64::from(high == 0))]
        } else {
            Vec::new()
        },
        equalities_many: (config.input_branches > 2).then(|| {
            make_many_equalities(sks, &(0..config.input_branches as u64).collect::<Vec<_>>())
        }),
        ceil_branch_digits: make_branch_digit_luts(config, sks, &config.ceil_with_offset),
        floor_branch_digits: make_branch_digit_luts(config, sks, &config.floor_shifted),
        gate_digit: sks.generate_lookup_table_bivariate(|condition, digit| condition * digit),
        outer_high_equalities: if config.outer_highs.as_slice() == [0, 1] {
            vec![sks.generate_lookup_table(|high| u64::from(high == 0))]
        } else {
            Vec::new()
        },
        outer_high_equalities_many: (config.outer_highs.as_slice() != [0, 1])
            .then(|| make_many_equalities(sks, &config.outer_highs)),
        outer_mid_equalities: config
            .outer_mid_selectors
            .iter()
            .cloned()
            .map(|mids| sks.generate_lookup_table(move |mid| u64::from(mids.contains(&mid))))
            .collect(),
        outer_base_digits,
        outer_residual_digits,
        one_hot_refresh: {
            let max_row_residual = config.max_row_residual;
            sks.generate_lookup_table(move |value| value.min(max_row_residual))
        },
        residual_split_digits: if config.t == 32 {
            (0..2)
                .map(|digit| {
                    sks.generate_lookup_table(move |value| {
                        (value / RADIX_BASE.pow(digit)) % RADIX_BASE
                    })
                })
                .collect()
        } else {
            Vec::new()
        },
        residual_split_digits_many: (config.t == 64).then(|| {
            let low = |value| value % RADIX_BASE;
            let high = |value| (value / RADIX_BASE) % RADIX_BASE;
            sks.generate_many_lookup_table(&[&low, &high])
        }),
    }
}

fn transform_input(
    config: &Config,
    sks: &ShortintServerKey,
    low: &ShortintCiphertext,
    high: &ShortintCiphertext,
    digit_luts: &[BranchDigitLut],
    luts: &AlgorithmLuts,
) -> RadixCiphertext {
    let (equalities, branch_digits) = rayon::join(
        || {
            if config.input_branches == 2 {
                let mut high_bit = high.clone();
                high_bit.degree = Degree::new(1);
                let not_high = sks.apply_lookup_table(&high_bit, &luts.equalities[0]);
                vec![not_high, high_bit]
            } else {
                sks.apply_many_lookup_table(
                    high,
                    luts.equalities_many
                        .as_ref()
                        .expect("the four-branch input route has a many-LUT"),
                )
            }
        },
        || {
            digit_luts
                .par_iter()
                .map(|lut| match lut {
                    BranchDigitLut::Variable(lut) => Some(sks.apply_lookup_table(low, lut)),
                    BranchDigitLut::Zero | BranchDigitLut::Constant(_) => None,
                })
                .collect::<Vec<_>>()
        },
    );
    let gated = (0..config.input_branches * config.radix_blocks)
        .into_par_iter()
        .map(|index| {
            let branch = index / config.radix_blocks;
            match &digit_luts[index] {
                BranchDigitLut::Zero => sks.create_trivial(0),
                BranchDigitLut::Constant(value) => {
                    let mut selected = equalities[branch].clone();
                    sks.unchecked_scalar_mul_assign(&mut selected, *value as u8);
                    selected
                }
                BranchDigitLut::Variable(_) => sks.unchecked_apply_lookup_table_bivariate(
                    &equalities[branch],
                    branch_digits[index]
                        .as_ref()
                        .expect("a variable branch digit has an evaluated LUT"),
                    &luts.gate_digit,
                ),
            }
        })
        .collect::<Vec<_>>();
    let blocks = (0..config.radix_blocks)
        .into_par_iter()
        .map(|block| {
            let mut digit = gated[block].clone();
            for branch in 1..config.input_branches {
                sks.unchecked_add_assign(&mut digit, &gated[branch * config.radix_blocks + block]);
            }
            digit.degree = Degree::new((RADIX_BASE - 1) as usize);
            digit
        })
        .collect::<Vec<_>>();
    RadixCiphertext::from(blocks)
}

fn pack_base4_pair(
    sks: &ShortintServerKey,
    low_digit: &ShortintCiphertext,
    high_digit: &ShortintCiphertext,
) -> ShortintCiphertext {
    let mut packed = high_digit.clone();
    sks.unchecked_scalar_mul_assign(&mut packed, RADIX_BASE as u8);
    sks.unchecked_add_assign(&mut packed, low_digit);
    packed
}

fn sum_mutually_exclusive_residuals(
    config: &Config,
    sks: &ShortintServerKey,
    values: &[ShortintCiphertext],
    refresh: &LookupTableOwned,
) -> ShortintCiphertext {
    assert!(!values.is_empty());
    let group_values = config
        .outer_groups
        .iter()
        .enumerate()
        .map(|(group, outer_group)| {
            let mut matching = config
                .outer_residuals
                .iter()
                .enumerate()
                .filter(|(_, residual)| residual.group == group)
                .map(|(index, _)| values[index].clone());
            let mut value = matching
                .next()
                .expect("every nonconstant group has a residual branch");
            for residual in matching {
                sks.unchecked_add_assign(&mut value, &residual);
            }
            value.degree = Degree::new(outer_group.max_residual as usize);
            value
        })
        .collect::<Vec<_>>();

    let mut current = config
        .residual_bins
        .par_iter()
        .map(|bin| {
            let mut value = group_values[bin[0]].clone();
            for &group in &bin[1..] {
                sks.unchecked_add_assign(&mut value, &group_values[group]);
            }
            sks.apply_lookup_table(&value, refresh)
        })
        .collect::<Vec<_>>();
    while current.len() > 2 {
        current = current
            .par_chunks(2)
            .map(|chunk| {
                if chunk.len() == 1 {
                    return chunk[0].clone();
                }
                let mut sum = chunk[0].clone();
                sks.unchecked_add_assign(&mut sum, &chunk[1]);
                sks.apply_lookup_table(&sum, refresh)
            })
            .collect();
    }
    let mut sum = current[0].clone();
    for value in &current[1..] {
        sks.unchecked_add_assign(&mut sum, value);
    }
    sum.degree = Degree::new(config.max_row_residual as usize);
    sum
}

fn evaluate_outer(
    config: &Config,
    sks: &ServerKey,
    shortint_sks: &ShortintServerKey,
    shifted_delta: &RadixCiphertext,
    luts: &AlgorithmLuts,
) -> RadixCiphertext {
    let blocks = shifted_delta.blocks();
    let low = pack_base4_pair(shortint_sks, &blocks[0], &blocks[1]);
    let mid = pack_base4_pair(shortint_sks, &blocks[2], &blocks[3]);
    let mut high = if blocks.len() == 5 {
        blocks[4].clone()
    } else {
        pack_base4_pair(shortint_sks, &blocks[4], &blocks[5])
    };
    high.degree = Degree::new((config.max_shifted_delta / (OUTER_CHUNK * OUTER_CHUNK)) as usize);

    let ((high_equalities, mid_equalities), (base_branch_digits, residual_digits)) = rayon::join(
        || {
            rayon::join(
                || {
                    if config.outer_highs.as_slice() == [0, 1] {
                        let mut high_bit = high.clone();
                        high_bit.degree = Degree::new(1);
                        let not_high = shortint_sks
                            .apply_lookup_table(&high_bit, &luts.outer_high_equalities[0]);
                        vec![not_high, high_bit]
                    } else {
                        shortint_sks.apply_many_lookup_table(
                            &high,
                            luts.outer_high_equalities_many
                                .as_ref()
                                .expect("the outer high route has a many-LUT"),
                        )
                    }
                },
                || {
                    luts.outer_mid_equalities
                        .par_iter()
                        .map(|lut| shortint_sks.apply_lookup_table(&mid, lut))
                        .collect::<Vec<_>>()
                },
            )
        },
        || {
            rayon::join(
                || {
                    luts.outer_base_digits
                        .par_iter()
                        .map(|lut| match lut {
                            BranchDigitLut::Variable(lut) => {
                                Some(shortint_sks.apply_lookup_table(&mid, lut))
                            }
                            BranchDigitLut::Zero | BranchDigitLut::Constant(_) => None,
                        })
                        .collect::<Vec<_>>()
                },
                || {
                    luts.outer_residual_digits
                        .par_iter()
                        .map(|lut| shortint_sks.apply_lookup_table(&low, lut))
                        .collect::<Vec<_>>()
                },
            )
        },
    );

    let high_positions = config
        .outer_highs
        .iter()
        .copied()
        .enumerate()
        .map(|(index, value)| (value, index))
        .collect::<BTreeMap<_, _>>();
    let (base_gated, row_conditions) = rayon::join(
        || {
            (0..config.outer_highs.len() * QUOTIENT_RADIX_BLOCKS)
                .into_par_iter()
                .map(|index| {
                    let branch = index / QUOTIENT_RADIX_BLOCKS;
                    match &luts.outer_base_digits[index] {
                        BranchDigitLut::Zero => shortint_sks.create_trivial(0),
                        BranchDigitLut::Constant(value) => {
                            let mut selected = high_equalities[branch].clone();
                            shortint_sks
                                .unchecked_scalar_mul_assign(&mut selected, *value as u8);
                            selected
                        }
                        BranchDigitLut::Variable(_) => {
                            shortint_sks.unchecked_apply_lookup_table_bivariate(
                                &high_equalities[branch],
                                base_branch_digits[index]
                                    .as_ref()
                                    .expect("a variable outer-base digit has an evaluated LUT"),
                                &luts.gate_digit,
                            )
                        }
                    }
                })
                .collect::<Vec<_>>()
        },
        || {
            config
                .outer_groups
                .par_iter()
                .map(|outer_group| {
                    shortint_sks.unchecked_apply_lookup_table_bivariate(
                        &high_equalities[high_positions[&outer_group.high]],
                        &mid_equalities[outer_group.mid_selector],
                        &luts.gate_digit,
                    )
                })
                .collect::<Vec<_>>()
        },
    );

    let residual_gated = (0..config.outer_residuals.len())
        .into_par_iter()
        .map(|index| {
            let group = config.outer_residuals[index].group;
            shortint_sks.unchecked_apply_lookup_table_bivariate(
                &row_conditions[group],
                &residual_digits[index],
                &luts.gate_digit,
            )
        })
        .collect::<Vec<_>>();

    let base_blocks = (0..QUOTIENT_RADIX_BLOCKS)
        .map(|digit| {
            let mut value = base_gated[digit].clone();
            for branch in 1..config.outer_highs.len() {
                shortint_sks.unchecked_add_assign(
                    &mut value,
                    &base_gated[branch * QUOTIENT_RADIX_BLOCKS + digit],
                );
            }
            value.degree = Degree::new((RADIX_BASE - 1) as usize);
            value
        })
        .collect::<Vec<_>>();
    let residual_low = sum_mutually_exclusive_residuals(
        config,
        shortint_sks,
        &residual_gated,
        &luts.one_hot_refresh,
    );
    let residual_blocks = if config.t == 32 {
        luts.residual_split_digits
            .par_iter()
            .map(|lut| shortint_sks.apply_lookup_table(&residual_low, lut))
            .collect::<Vec<_>>()
    } else {
        shortint_sks.apply_many_lookup_table(
            &residual_low,
            luts.residual_split_digits_many
                .as_ref()
                .expect("the t=64 residual split has a many-LUT"),
        )
    };
    let residual = RadixCiphertext::from(vec![
        residual_blocks[0].clone(),
        residual_blocks[1].clone(),
        shortint_sks.create_trivial(0),
    ]);
    let base = RadixCiphertext::from(base_blocks);
    sks.add_parallelized(&base, &residual)
}

fn evaluate_outer_threshold(
    config: &Config,
    sks: &ServerKey,
    shifted_delta: &RadixCiphertext,
) -> RadixCiphertext {
    let indicators = (1..config.t as usize)
        .into_par_iter()
        .map(|level| {
            sks.scalar_ge_parallelized(shifted_delta, config.thresholds[level - 1])
                .into_radix::<RadixCiphertext>(QUOTIENT_RADIX_BLOCKS, sks)
        })
        .collect::<Vec<_>>();
    sks.sum_ciphertexts_parallelized(&indicators)
        .expect("the quotient threshold list is nonempty")
}

fn evaluate_algorithm1(
    config: &Config,
    dividend: u64,
    divisor: u64,
    cks: &RadixClientKey,
    sks: &ServerKey,
    luts: &AlgorithmLuts,
    outer_route: OuterRoute,
) -> Evaluation {
    let integer_cks: &tfhe::integer::ClientKey = cks.as_ref();
    let shortint_cks: &ShortintClientKey = integer_cks.as_ref();
    let shortint_sks: &ShortintServerKey = sks.as_ref();
    let encrypted_m_low = shortint_cks.unchecked_encrypt(dividend % INPUT_CHUNK);
    let encrypted_m_high = shortint_cks.unchecked_encrypt(dividend / INPUT_CHUNK);
    let encrypted_d_low = shortint_cks.unchecked_encrypt(divisor % INPUT_CHUNK);
    let encrypted_d_high = shortint_cks.unchecked_encrypt(divisor / INPUT_CHUNK);

    reset_pbs_count();
    let started = Instant::now();
    let (encrypted_ceil, encrypted_floor) = rayon::join(
        || {
            transform_input(
                config,
                shortint_sks,
                &encrypted_m_low,
                &encrypted_m_high,
                &luts.ceil_branch_digits,
                luts,
            )
        },
        || {
            transform_input(
                config,
                shortint_sks,
                &encrypted_d_low,
                &encrypted_d_high,
                &luts.floor_branch_digits,
                luts,
            )
        },
    );
    let input_ms = started.elapsed().as_secs_f64() * 1000.0;
    let input_pbs = get_pbs_count();
    let subtraction_started = Instant::now();
    let shifted_delta = sks.sub_parallelized(&encrypted_ceil, &encrypted_floor);
    let subtraction_ms = subtraction_started.elapsed().as_secs_f64() * 1000.0;
    let after_subtraction_pbs = get_pbs_count();
    let outer_started = Instant::now();

    let quotient = match outer_route {
        OuterRoute::Packed => evaluate_outer(config, sks, shortint_sks, &shifted_delta, luts),
        OuterRoute::Threshold => evaluate_outer_threshold(config, sks, &shifted_delta),
    };
    let outer_ms = outer_started.elapsed().as_secs_f64() * 1000.0;
    let final_pbs_count = get_pbs_count();

    Evaluation {
        ceil_log_with_offset: encrypted_ceil,
        floor_log_shifted: encrypted_floor,
        shifted_delta,
        quotient,
        pbs_count: final_pbs_count,
        elapsed_ms: started.elapsed().as_secs_f64() * 1000.0,
        input_pbs,
        subtraction_pbs: after_subtraction_pbs.saturating_sub(input_pbs),
        outer_pbs: final_pbs_count.saturating_sub(after_subtraction_pbs),
        input_ms,
        subtraction_ms,
        outer_ms,
    }
}

fn plaintext_quotient(config: &Config, shifted_delta: u64) -> u64 {
    config
        .thresholds
        .iter()
        .filter(|&&threshold| shifted_delta >= threshold)
        .count() as u64
}

fn fused_outer_quotient(config: &Config, shifted_delta: u64) -> u64 {
    let row = shifted_delta / OUTER_CHUNK;
    let high = row / OUTER_CHUNK;
    let mid = row % OUTER_CHUNK;
    let low = shifted_delta % OUTER_CHUNK;
    let base = config.outer_base_values[row as usize];
    let residual = config
        .outer_groups
        .iter()
        .filter(|group| group.high == high && group.mids.contains(&mid))
        .map(|group| group.residual_values[low as usize])
        .sum::<u64>();
    base + residual
}

fn verify_plaintext(config: &Config) -> usize {
    let mut cases = 0;
    for dividend in 0..config.t {
        for divisor in 1..config.t {
            let shifted_delta = (config.ceil_shifted[dividend as usize] as i64
                - config.floor_shifted[divisor as usize] as i64
                + config.delta_offset as i64) as u64;
            assert!(shifted_delta <= config.max_shifted_delta);
            assert_eq!(
                plaintext_quotient(config, shifted_delta),
                dividend / divisor
            );
            assert_eq!(fused_outer_quotient(config, shifted_delta), dividend / divisor);
            cases += 1;
        }
    }
    cases
}

fn deterministic_cases(t: u64) -> Vec<(u64, u64)> {
    let preferred = [
        (0, t - 1),
        (1, 1),
        (t - 1, 1),
        (t - 1, t - 1),
        (t / 2 - 2, t - 3),
        (t - 2, 3),
        (t / 2 - 1, 2),
        (t / 2, 3),
        (t - 3, 4),
        (t / 2 + 1, t / 2),
    ];
    let mut cases = preferred.to_vec();
    for dividend in 0..t {
        for divisor in 1..t {
            if !cases.contains(&(dividend, divisor)) {
                cases.push((dividend, divisor));
            }
        }
    }
    cases
}

fn parse_args() -> Result<(u64, Selection, OuterRoute), String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let mut t = None;
    let mut selection = Selection::Default;
    let mut outer_route = OuterRoute::Packed;
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--t" => {
                t = Some(
                    args.get(index + 1)
                        .ok_or("--t requires 32 or 64")?
                        .parse::<u64>()
                        .map_err(|_| "invalid --t value")?,
                );
                index += 2;
            }
            "--case" => {
                let m = args
                    .get(index + 1)
                    .ok_or("--case requires m and d")?
                    .parse::<u64>()
                    .map_err(|_| "invalid dividend")?;
                let d = args
                    .get(index + 2)
                    .ok_or("--case requires m and d")?
                    .parse::<u64>()
                    .map_err(|_| "invalid divisor")?;
                selection = Selection::One(m, d);
                index += 3;
            }
            "--samples" => {
                selection = Selection::Count(
                    args.get(index + 1)
                        .ok_or("--samples requires a count")?
                        .parse::<usize>()
                        .map_err(|_| "invalid sample count")?,
                );
                index += 2;
            }
            "--exhaustive-encrypted" => {
                selection = Selection::Exhaustive;
                index += 1;
            }
            "--plaintext-only" => {
                selection = Selection::PlaintextOnly;
                index += 1;
            }
            "--outer-route" => {
                outer_route = match args.get(index + 1).map(String::as_str) {
                    Some("packed") => OuterRoute::Packed,
                    Some("threshold") => OuterRoute::Threshold,
                    _ => return Err("--outer-route requires packed or threshold".into()),
                };
                index += 2;
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }
    Ok((
        t.ok_or("--t 32 or --t 64 is required")?,
        selection,
        outer_route,
    ))
}

fn run() -> Result<(), String> {
    let (t, selection, outer_route) = parse_args()?;
    let config = make_config(t)?;
    let plaintext_cases = verify_plaintext(&config);
    println!(
        "PLAINTEXT_EXHAUSTIVE_PASS,t={},M={},base={BASE},cases={plaintext_cases},delta_offset={},max_shifted_delta={},input_chunks={}",
        config.t,
        config.m_scale,
        config.delta_offset,
        config.max_shifted_delta,
        config.input_branches
    );
    if matches!(selection, Selection::PlaintextOnly) {
        return Ok(());
    }
    let outer_route_name = match outer_route {
        OuterRoute::Packed => "packed_nibble_reachable_row_fusion_PBS",
        OuterRoute::Threshold => "parallel_threshold_PBS_circuits",
    };
    println!(
        "ALGORITHM1_CONFIG,t={},M={},base={BASE},radix_base={RADIX_BASE},intermediate_radix_blocks={},quotient_radix_blocks={QUOTIENT_RADIX_BLOCKS},parameter=PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,input_route=encrypted_16_value_chunks,offset_fused=true,constant_digits_elided=true,parallel_luts=true,outer_high_branches={},outer_mid_selectors={},outer_residual_groups={},outer_residual_components={},outer_residual_bins={},outer_route={outer_route_name}",
        config.t,
        config.m_scale,
        config.radix_blocks,
        config.outer_highs.len(),
        config.outer_mid_selectors.len(),
        config.outer_groups.len(),
        config.outer_residuals.len(),
        config.residual_bins.len()
    );
    let key_started = Instant::now();
    let (cks, mut sks) = gen_keys_radix(
        PARAM_MULTI_BIT_MESSAGE_2_CARRY_2_GROUP_3_KS_PBS,
        config.radix_blocks,
    );
    sks.set_deterministic_pbs_execution(false);
    println!(
        "KEYGEN_MS,{:.6}",
        key_started.elapsed().as_secs_f64() * 1000.0
    );
    let shortint_sks: &ShortintServerKey = sks.as_ref();
    let luts = make_luts(&config, shortint_sks);

    let all_cases = deterministic_cases(config.t);
    let selected = match selection {
        Selection::Default => all_cases[..3].to_vec(),
        Selection::One(m, d) => {
            if m >= config.t || !(1..config.t).contains(&d) {
                return Err("the selected case is outside the configured domain".into());
            }
            vec![(m, d)]
        }
        Selection::Count(count) => {
            if count == 0 || count > all_cases.len() {
                return Err(format!("--samples must be in 1..={}", all_cases.len()));
            }
            all_cases[..count].to_vec()
        }
        Selection::Exhaustive => (0..config.t)
            .flat_map(|m| (1..config.t).map(move |d| (m, d)))
            .collect(),
        Selection::PlaintextOnly => unreachable!(),
    };

    let mut total_ms = 0.0;
    let mut total_pbs = 0_u64;
    for (index, (dividend, divisor)) in selected.iter().copied().enumerate() {
        let result =
            evaluate_algorithm1(&config, dividend, divisor, &cks, &sks, &luts, outer_route);
        let transformed_m_with_offset: u64 = cks.decrypt(&result.ceil_log_with_offset);
        let transformed_m = transformed_m_with_offset - config.delta_offset;
        let transformed_d: u64 = cks.decrypt(&result.floor_log_shifted);
        let shifted_delta: u64 = cks.decrypt(&result.shifted_delta);
        let actual: u64 = cks.decrypt(&result.quotient);
        let expected = dividend / divisor;
        if transformed_m_with_offset != config.ceil_with_offset[dividend as usize]
            || transformed_m != config.ceil_shifted[dividend as usize]
            || transformed_d != config.floor_shifted[divisor as usize]
            || shifted_delta != transformed_m_with_offset - transformed_d
            || actual != expected
        {
            return Err(format!(
                "encrypted check failed for {dividend}/{divisor}: transformed_m={transformed_m}, transformed_d={transformed_d}, shifted_delta={shifted_delta}, actual={actual}, expected={expected}"
            ));
        }
        total_ms += result.elapsed_ms;
        total_pbs += result.pbs_count;
        println!(
            "ENCRYPTED_RESULT,index={index},m={dividend},d={divisor},clog_plus_1={transformed_m},floorlog_plus_1={transformed_d},shifted_delta={shifted_delta},expected={expected},actual={actual},pbs_count={},elapsed_ms={:.6}",
            result.pbs_count, result.elapsed_ms
        );
        println!(
            "ENCRYPTED_STAGES,index={index},input_pbs={},input_ms={:.6},subtraction_pbs={},subtraction_ms={:.6},outer_pbs={},outer_ms={:.6}",
            result.input_pbs,
            result.input_ms,
            result.subtraction_pbs,
            result.subtraction_ms,
            result.outer_pbs,
            result.outer_ms
        );
    }
    println!(
        "ENCRYPTED_SUMMARY,PASS,t={},cases={},average_pbs={:.3},average_ms={:.6},total_pbs={total_pbs}",
        config.t,
        selected.len(),
        total_pbs as f64 / selected.len() as f64,
        total_ms / selected.len() as f64
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
