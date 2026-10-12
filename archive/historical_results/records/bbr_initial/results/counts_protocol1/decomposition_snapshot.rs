use crate::files::{
    import_parameters_from_table, read_betas, read_encodings, read_gammas, read_phis_from_file,
};
use std::collections::HashMap;

use crate::files::{read_parameters_decompositions, read_sbox};

use rayon::iter::{IntoParallelIterator, ParallelIterator};
use tfhe::gadget::prelude::*;


type Gammas = Vec<Vec<u64>>; //TODO: renommer d_i in the paper
type Betas = Vec<Vec<u64>>;
type Phis = HashMap<(i64, usize), (Vec<u64>, Vec<u64>)>;
type Sbox = Vec<u64>;

pub struct Decomposition {
    log_s: usize,
    s: u64,
    p: u64,
    n: usize,
    l: usize,
    t_is: Vec<usize>,
    betas: Betas,
    gammas: Gammas,
    phis: Phis,
    pub sbox: Sbox,
    pub parameters: BooleanParameters,
    pub encodings: Vec<Encoding>,
    pub cost_pbs: f64,
}

impl Decomposition {
    pub fn load_decomposition(log_s: usize, p: u64, n: usize, perror: usize, mode: &str) -> Self {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(format!("../../decompositions/{}", mode));

        let filename_gammas = path.join(format!("d_{}_{}", p, n));
        let filename_betas = path.join(format!("betas_{}_{}", p, n));
        let filename_phis = path.join(format!("new_phis_{}_{}", p, n));
        let filename_sbox = path.join(format!("sbox_{}_{}", p, n));
        let filename_parameters = path.join(format!("parameters_{}_{}", p, n));
        let filename_encodings = path.join(format!("encodings_{}_{}", p, n));

        let (l, t_is, nu) = read_parameters_decompositions(&filename_parameters);

        let parameters = import_parameters_from_table(p, nu, perror).unwrap();

        let gammas = read_gammas(&filename_gammas).unwrap();
        let betas: Vec<Vec<u64>> = read_betas(&filename_betas).unwrap();
        let phis = read_phis_from_file(&filename_phis).unwrap();
        let sbox = read_sbox(&filename_sbox).unwrap();
        let encodings = read_encodings(&filename_encodings, 1 << log_s, p);

        Self {
            log_s,
            s: 1 << log_s,
            p,
            n,
            l,
            t_is,
            betas,
            gammas,
            phis,
            sbox,
            parameters,
            encodings,
            cost_pbs: 0.0,
        }
    }

    pub fn compute_theoretical_cost(&self) -> f64 {
        let n_pbs = self.l + 2 * self.t_is[..self.t_is.len() - 1].iter().sum::<usize>();
        println!("cost:{} and n_pbs:{}", self.cost_pbs, n_pbs);
        self.cost_pbs * n_pbs as f64
    }


    pub fn partial_lut_evaluation(
        &self,
        inputs: &Vec<Ciphertext>,
        server_key: &ServerKey,
        m_outputs_to_evaluate: usize,
        client_key_debug: &ClientKey,
    ) -> Vec<Ciphertext> {
        let mut x_ins = inputs.clone();
        // Evaluation de la chaine de base
        for i in 0..self.l {
            assert_eq!(x_ins.len(), self.n + i);
            x_ins.push(compute_function_phi(
                &x_ins,
                &self.phis[&(-1, i)].0,
                &self.phis[&(-1, i)].1,
                self.p,
                &server_key,
            ));
        }

        // evaluation des m sorties
        let mut output: Vec<Ciphertext> = vec![];
        assert!(m_outputs_to_evaluate <= self.n);
        for index_bit_out in 0..m_outputs_to_evaluate {
            let t_i = self.t_is[index_bit_out];
            let n_i = self.n + self.l + self.t_is[..index_bit_out].iter().sum::<usize>();

            let mut products: Vec<Ciphertext> = (0..t_i).map(|i|{
                let right_hand_term = weighted_sum(
                    &x_ins,
                    &self.gammas[index_bit_out][i * n_i..(i + 1) * n_i].to_vec(),
                    self.p,
                    &server_key,
                );

                let left_hand_term =
                    weighted_sum(
                        &x_ins,
                        &self.betas[index_bit_out][i * n_i..(i + 1) * n_i].to_vec(),
                        self.p,
                        &server_key,
                    );

                mult(&left_hand_term, &right_hand_term, self.p, &server_key)
            }).collect();
            products.iter().for_each(|xi| x_ins.push(xi.clone()));
            // linear term
            let linear_term = weighted_sum(
                &x_ins,
                &self.betas[index_bit_out][t_i * n_i..].to_vec(),
                self.p,
                &server_key,
            );
            products.push(linear_term);

            let bit_out = server_key.simple_sum(&products);
            output.push(bit_out);
        }
        output
    }
}

fn weighted_sum(
    inputs: &Vec<Ciphertext>,
    alphas: &Vec<u64>,
    p: u64,
    server_key: &ServerKey,
) -> Ciphertext {
    let weighted_terms = inputs
        .iter()
        .zip(alphas)
        .map(|(input, alpha)| server_key.simple_mul_constant(input, *alpha, p))
        .collect();
    server_key.simple_sum(&weighted_terms)
}

fn compute_function_phi(
    inputs: &Vec<Ciphertext>,
    alphas: &Vec<u64>,
    lut: &Vec<u64>,
    p: u64,
    server_key: &ServerKey,
) -> Ciphertext {
    assert_eq!(inputs.len(), alphas.len());

    let sum = weighted_sum(&inputs, &alphas, p, &server_key);

    server_key.apply_lut(&sum, &Encoding::new_trivial(p), &|x| lut[x as usize])
}

fn mult(x: &Ciphertext, y: &Ciphertext, p: u64, server_key: &ServerKey) -> Ciphertext {
    let encoding = Encoding::new_trivial(p);
    // division par [4] mod p
    let inv_4 = match p {
        3 => 1,
        5 => 4,
        17 => 13,
        _ => todo!(),
    };
    let lut_square = |x: u64| x * x * inv_4 % p;
    let lut_minus_square = |x: u64| ((p - 1) * x * x) * inv_4 % p; //la même que celle au dessus, mais qui calcule le - devant en plus
    let sum_squared = server_key.apply_lut(
        &server_key.simple_sum(&vec![x.clone(), y.clone()]),
        &encoding,
        &lut_square,
    );
    let diff = server_key.simple_sum(
        &vec![
            vec![x.clone()],
            vec![y.clone(); (p - 1).try_into().unwrap()],
        ]
        .concat(),
    ); // + (p-1) * y = - y in Zp
    let diff_squared = server_key.apply_lut(&diff, &encoding, &lut_minus_square);
    let result = server_key.simple_sum(&vec![sum_squared, diff_squared]);

    result
}

// DCC comparison adapter: explicit fixed-function a=0 certificate, using the
// author's unmodified partial_lut_evaluation and atomic-function implementations.
impl Decomposition {
    pub fn certified_count(n: usize, interval: bool, parameters: BooleanParameters) -> Self {
        let p = 17;
        assert!(n == 12 || n == 16);
        let mut phis = HashMap::new();
        let lut = (0..p).map(|s| if interval {
            ((n/3) as u64 <= s && s <= (2*n/3) as u64) as u64
        } else { (s >= (n/2) as u64) as u64 }).collect();
        phis.insert((-1, 0), (vec![1;n], lut));
        let mut beta = vec![0;n]; beta.push(1);
        Self {log_s:1,s:2,p,n,l:1,t_is:vec![0],betas:vec![beta],
            gammas:vec![vec![]],phis,sbox:vec![],parameters,
            encodings:vec![Encoding::new_trivial(p)],cost_pbs:0.0}
    }
}
