"""Recompute the targeted run; never infer encrypted correctness from timing alone."""
import argparse, csv, hashlib, io, json, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',default='div4_attempt1',help='Existing run directory name under results (default: released run).')
args=parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',args.run): parser.error('Invalid run label')
run = ROOT / 'results' / args.run
log = (run / 'run.log').read_text(encoding='utf-8')
assert (run / 'exit_code.txt').read_text().strip() == '0'
assert 'COMPLETE,measured=30,warmups=5,mismatches=0' in log
header = 'phase,index,m,d,expected,actual,total_ms,input_conversion_ms,lut_ms,abs_error'
lines = [line for line in log.splitlines() if line.startswith(('warmup,', 'measured,'))]
rows = list(csv.DictReader(io.StringIO(header + '\n' + '\n'.join(lines))))
assert len(rows) == 35
for row in rows:
    assert int(row['actual']) == int(row['expected']) == int(row['m']) // int(row['d'])
measured = [row for row in rows if row['phase'] == 'measured']
assert len(measured) == 30

summary = {
    'status': 'completed', 'method': 'Refined-LHE author-routine composition DIV4',
    'upstream_commit': '9b0426e8e197020a4bf40776cc03641e6cf9b90e',
    'parameter': 'INT_LHE_BASE_16', 'extract_size': 2,
    'warmups': 5, 'samples': 30, 'mismatches': 0,
    'input': 'two 4-bit no-padding big-LWE ciphertexts, delta=2^60',
    'output': 'one 4-bit padded big-LWE ciphertext, delta=2^59',
    'included': ['two input CBS conversions', 'online allocations', 'final selector Fourier conversion', 'fresh LUT accumulator clone', '8 CMUX operations', 'output extraction'],
    'excluded': ['key generation', 'public LUT and identity-accumulator generation', 'input encryption', 'output decryption'],
    'failure_probability': 'No complete-path numerical failure bound provided by the selected author parameter definition. Empirical zero mismatches are not a cryptographic guarantee.',
}
for metric in ('total_ms','input_conversion_ms','lut_ms'):
    values = [float(row[metric]) for row in measured]
    summary[metric] = {'mean': statistics.mean(values), 'population_sd': statistics.pstdev(values),
                       'median': statistics.median(values), 'min': min(values), 'max': max(values)}
reference = ROOT/'results/reference_v1/division16.log'
if reference.exists():
    oldrows = [dict(item.split('=',1) for item in line.split(',')[1:])
               for line in reference.read_text().splitlines() if line.startswith('ENCRYPTED_RESULT,')]
    assert [(int(r['m']),int(r['d'])) for r in oldrows] == [(int(r['m']),int(r['d'])) for r in measured]
    summary['same_ordered_inputs_as_v1'] = True
    oldvalues = [float(r['elapsed_ms']) for r in oldrows]
    summary['reference_v1'] = {'method':'DCC supplementary t=16 run, not rerun in v2',
        'samples':30, 'warmups':0, 'mean_ms':statistics.mean(oldvalues),
        'population_sd_ms':statistics.pstdev(oldvalues), 'median_ms':statistics.median(oldvalues),
        'compatibility_note':'Same host, function and ordered inputs. Different input ciphertext conventions, TFHE versions, parameters, scheduling and warmups; not an equal-security or interface-identical benchmark.'}
source = run/'source_snapshot.rs'
summary['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
assert source.read_bytes() == (ROOT/'source/refined-tfhe-lhe/benches/bench_targeted_div4.rs').read_bytes()
out = ROOT/'results/summary' if args.run=='div4_attempt1' else run/'summary'
out.mkdir(exist_ok=True)
with (out/'all_trials.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader();writer.writerows(rows)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
with (out/'summary.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=['metric','n','mean','population_sd','median','min','max'])
    writer.writeheader()
    for metric in ('total_ms','input_conversion_ms','lut_ms'):
        writer.writerow({'metric':metric,'n':30,**summary[metric]})
print(json.dumps(summary,indent=2))
