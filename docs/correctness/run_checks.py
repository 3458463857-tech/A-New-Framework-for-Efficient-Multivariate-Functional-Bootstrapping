#!/usr/bin/env python3
"""Capture the deterministic check transcript and build machine-readable ledgers."""
from pathlib import Path
import csv, hashlib, json, math, subprocess, sys
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 commands=[['audit_all_inputs.py','--source-dir','../final_experiments/source/section3/src/bin'],
           ['audit_controls.py'],['audit_signed.py']]
 logs=[]
 for args in commands:
  p=subprocess.run([sys.executable]+args,cwd=HERE,text=True,capture_output=True)
  logs+=['COMMAND: python3 '+' '.join(args),'EXIT_CODE: '+str(p.returncode),p.stdout,p.stderr]
  (HERE/'results/checks.log').write_text('\n'.join(logs))
  if p.returncode:raise SystemExit(p.returncode)
 runs=json.loads((HERE.parent/'final_experiments/summary/all_results.json').read_text())['runs']
 parameters={r['parameters']['name']:r['parameters'] for r in runs}
 fields=sorted({k for p in parameters.values() for k in p})
 with (HERE/'FINAL_PARAMETERS.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(parameters.values())
 ledger=[]
 for r in runs:
  method=r['method'];size=int(r['size'])
  if method=='dcc':
   events={16:46,32:118,64:219}[size];local=-64.442
   grade='I: full-domain ideal/metadata graph; II: conditional calibration C; III: 35 correct encrypted observations'
  elif method=='native':
   events={16:66,32:117,64:117}[size];local=-64.442
   grade='I: source-path induction and local integer checks; II: conditional calibration C; III: 35 correct encrypted observations'
  elif method=='count':
   events=1;local=-64.078
   grade='I: all bit vectors and checked sum; II: conditional calibration C; III: 35 correct encrypted observations'
  else:
   events=local=None
   grade='I: adapter/interface/index checks; III: 35 correct encrypted observations; no composite numeric failure bound'
  row={k:r[k] for k in ('run','method','size','predicate','source_sha256','input_manifest_sha256','cargo_lock_sha256','raw_log_sha256')}
  row|={'evidence_grade':grade,'conservative_scalar_events':events,
        'conditional_model_log2':local+math.log2(events) if events else None,
        'conditional_model_probability':events*2**local if events else None,
        'strict_cryptographic_tail_bound_proved':False,
        'condition':'Assumption C in FAILURE_ANALYSIS.md; otherwise retain p_in + sum p_j + p_out, with uncalibrated terms unknown.'}
  ledger.append(row)
 result={'scope':'Final protocol-1 rows only. No equation of library parameter labels with full-circuit guarantees.',
         'runs':ledger,'total_empirical_correct_observations':525,
         'check_sources_sha256':{p.name:sha(p) for p in HERE.glob('*.py')}}
 (HERE/'FINAL_CIRCUIT_MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: three deterministic checkers, 15 source/log bindings, signed interfaces; ledgers and parameters exported.')
if __name__=='__main__':main()
