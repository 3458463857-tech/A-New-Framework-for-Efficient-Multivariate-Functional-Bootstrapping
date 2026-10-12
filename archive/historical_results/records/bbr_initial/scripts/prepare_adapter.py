"""Apply the small, recorded harness additions to the pinned author snapshot."""
from pathlib import Path
import hashlib, json

root = Path(__file__).resolve().parents[1]
src = root / 'source/author/bench/HLUT-rs/src'
decomp = src / 'decomposition.rs'
original = decomp.read_text()
assert 'pub fn certified_count' not in original
decomp.write_text(original + '''
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
''')
files = src / 'files.rs'
s = files.read_text()
assert 'if ((nu as i64 - nu_record as i64) < 0)' in s
s = s.replace('if ((nu as i64 - nu_record as i64) < 0)',
    'if record[0].parse::<u64>().unwrap() == p && nu <= nu_record')
files.write_text(s)
print('Added fixed count certificate constructor; corrected parameter lookup to match p and inclusive nu.')
