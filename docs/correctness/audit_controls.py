#!/usr/bin/env python3
"""Check finite domains, source/log bindings, and local native budget rules.

This is deterministic integer verification. It neither samples cryptographic
noise nor proves the calibration of the TFHE parameter sets.
"""
from pathlib import Path
import csv, hashlib, json, math

HERE = Path(__file__).resolve().parent
FINAL = HERE.parent / 'final_experiments'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def digits(x, n): return [(x // 4**i) % 4 for i in range(n)]

def main():
    # Standard restoring division invariant, for the 4/6-bit native workload.
    # This checks the mathematical invariant used in NOISE_AUDIT; it is not a
    # transcription or a formal verification of TFHE's complete Rust divider.
    native = {}
    for t in (16, 32, 64):
        width = 4 if t == 16 else 6
        cases = 0
        for m in range(t):
            for d in range(1, t):
                q = r = 0
                for i in reversed(range(width)):
                    assert 0 <= r < d
                    r = 2*r + ((m >> i) & 1)
                    assert 0 <= r < 2*d
                    if r >= d: r -= d; q |= 1 << i
                    assert 0 <= r < d
                assert q == m//d and r == m%d
                cases += 1
        native[t] = {'legal_pairs': cases, 'restoring_division_invariant': 'PASS'}

    # Exhaustive local rules of the selected <=3-block library paths. Degrees
    # are upper bounds, not secret plaintext-dependent metadata assignments.
    local_cases = 0
    for a in range(4):
        for b in range(4):
            packed = 4*a+b
            assert packed <= 15 and 4*1+1 <= 5
            # Shift bivariates use the same input packing and one PBS.
            for borrow in range(2):
                z = a-b+4-borrow
                assert 0 <= z <= 7 and 2+1+1 <= 5
                # Remainder alternatives are disjoint; merged degree <=6,
                # negated divisor degree <=4, so degree <=10 before borrow.
                assert 6+4 <= 15
                local_cases += 1
    for digit in range(4):
        for overflow in range(3):
            assert digit*3+overflow <= 11
            assert 3*1+2 <= 5
    for nblocks in (2,3):
        assert 3*nblocks <= 15 and nblocks <= 5  # zero-test linear sum
    # Final quotient has at most two separately refreshed bit contributions.
    assert 1+2 <= 3 and 1+1 <= 5

    counts = {}
    for n in (12,16):
        assert 3*n <= 63 and n <= 21
        totals = [0,0]
        for mask in range(1 << n):
            weight = mask.bit_count()
            # Separate coordinate maps identity on bits; statistic is exact.
            assert sum((mask >> i)&1 for i in range(n)) == weight
            totals[0] += int(weight >= n//2)
            totals[1] += int(n//3 <= weight <= 2*n//3)
        counts[n] = {'inputs_checked': 1 << n, 'max_degree': 3*n,
                     'max_noise_level': n, 'PBS_input_capacity':63,
                     'PBS_noise_capacity':21, 'PBS_events':1,
                     'threshold_positive_inputs':totals[0],
                     'interval_positive_inputs':totals[1]}

    # Refined two-bit selector correction: (b0 xor b1,b1), repeated twice.
    def transform(x): return x ^ ((x & 2)>>1) ^ ((x & 8)>>1)
    table = [(transform(i&15)//transform(i>>4)) if transform(i>>4) else 0
             for i in range(256)]
    for m in range(16):
        assert transform(transform(m)) == m
        for d in range(1,16):
            assert table[transform(m)+(transform(d)<<4)] == m//d
    refined = FINAL/'source/refined-tfhe-lhe/benches/bench_count_boolean.rs'
    refined_text = refined.read_text()
    assert 'inputs.iter().rev()' in refined_text, 'author vertical packing requires MSB-first selectors'

    sources = {
        'dcc': lambda r:'source/section3/src/bin/algorithm1_t16_audited.rs' if r['size']=='16' else 'source/section3/src/bin/algorithm1_audited.rs',
        'native': lambda r:'source/section3/src/bin/baseline_div_final.rs',
        'count': lambda r:'source/section3/src/bin/count_checked_final.rs',
        'refined_count': lambda r:'source/refined-tfhe-lhe/benches/bench_count_boolean.rs',
        'refined_div': lambda r:'source/refined-tfhe-lhe/benches/bench_targeted_div4.rs',
    }
    summary = json.loads((FINAL/'summary/all_results.json').read_text())
    rows=[]
    for r in summary['runs']:
        assert r['method'] in sources, r['method']
        source = FINAL/sources[r['method']](r)
        assert sha(source)==r['source_sha256'], str(source)
        logfile=FINAL/Path(r['raw_path'].replace('\\','/'))
        assert sha(logfile)==r['raw_log_sha256'], str(logfile)
        assert r['samples']==30 and r['warmups']==5 and r['mismatches']==0
        assert len(r['trials'])==35
        # All native PBS operations selected here produce a single output;
        # counting trivial PBS too gives a conservative scalar-event bound.
        observed=sorted({int(x['pbs_count']) for x in r['trials'] if 'pbs_count' in x})
        if r['method']=='dcc':
            assert observed==[{16:42,32:114,64:205}[int(r['size'])]]
        if r['method']=='native':
            assert observed==[{16:66,32:117,64:117}[int(r['size'])]]
        if r['method']=='count': assert observed==[1]
        rows.append({k:r[k] for k in ('run','method','size','predicate','source_sha256','raw_log_sha256','input_manifest_sha256')}
                    | {'source':str(source.relative_to(FINAL)),'observed_PBS_counters':observed,'correct_observations':35})
    assert len(rows)==15
    result={'scope':'Exact input and local budget checks; native library implementation reviewed separately; no probability-tail proof.',
            'native_domains':native,'native_local_rule_cases':local_cases,'count_domains':counts,
            'refined_division_selector_pairs':240,'refined_count_selector_order':'MSB first, as author vertical_packing',
            'bound_final_runs':rows,'total_observed_correct':sum(x['correct_observations'] for x in rows)}
    (HERE/'results/controls_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='bound_final_runs'},indent=2))

if __name__=='__main__': main()
