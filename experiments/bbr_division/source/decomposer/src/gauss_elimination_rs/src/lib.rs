use pyo3::prelude::*;
use rayon::prelude::*;


fn divide_in_field(lhs: i64, rhs: i64, p: i64) -> i64 {
    assert!(rhs.rem_euclid(p) != 0, "division by zero in field");
    (lhs.rem_euclid(p) * mod_pow(rhs, p - 2, p)).rem_euclid(p)
}

fn mod_pow(mut base: i64, mut exp: i64, modu: i64) -> i64 {
    let mut result = 1i64;
    base = base.rem_euclid(modu);

    while exp > 0 {
        if exp % 2 == 1 {
            result = (result * base).rem_euclid(modu);
        }
        base = (base * base).rem_euclid(modu);
        exp /= 2;
    }

    result
}



#[pyfunction]
fn gauss_elimination(a: Vec<Vec<i64>>, b: Vec<i64>, p : i64) -> PyResult<Vec<Vec<i64>>> {

    let m = a.len();
    let n = a[0].len();

    let mut ab: Vec<Vec<i64>> = a.iter()
    .zip(b.iter())
    .map(|(row_a, &b_i)| {
        let mut row = Vec::with_capacity(n + 1);
        row.extend_from_slice(row_a);
        row.push(b_i);
        row
    })
    .collect();


    let mut h = 0;
    let mut k = 0;


    while h < m && k < n {
        let mut i_max = None;

        for i in h..m {
            if ab[i][k].rem_euclid(p) != 0 {
                i_max = Some(i);
                break;
            }
        }
        if let Some(i_piv) = i_max {
            // Swap the current row with the row of the max pivot
            ab.swap(h, i_piv);


            // Scale the pivot row (parallelizable)
            let pivot_value = ab[h][k];
            let pivot_row = ab[h].clone();
            ab[h][k..n + 1].par_iter_mut().for_each(|x| {
                *x = divide_in_field(*x, pivot_value, p);
            });


            // Perform row elimination (parallelizable)
            ab.par_iter_mut().enumerate().for_each(|(i, row)| {
                if i != h {
                    let factor = divide_in_field(row[k], pivot_value, p);
                    (k..n + 1).for_each(|j| {
                        row[j] = (row[j] - pivot_row[j]* factor).rem_euclid(p);
                    });
                }
            });

            h += 1;
            k += 1;
        }
    else{
        k += 1;
    }
    }
    Ok(ab)
}


/// A Python module implemented in Rust. The name of th     is function must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pymodule]
fn gauss_elimination_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(gauss_elimination, m)?)?;
    Ok(())
}


#[test]
fn test_gauss_elimination(){
    let a = vec![
        vec![1, 0, 2],
        vec![2, 2, 1],
        vec![0, 0, 1]
    ];

    let b = vec![0, 0, 0];
    let p = 3;
    let res = gauss_elimination(a, b, p);
    println!("{:?}", res);
}
