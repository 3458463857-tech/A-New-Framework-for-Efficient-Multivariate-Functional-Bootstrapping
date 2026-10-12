#!/usr/bin/env python3
"""Capture numbered excerpts and whole-source hashes from the pinned crate."""
from pathlib import Path
import argparse, hashlib, json
HERE=Path(__file__).resolve().parent
RANGES={
 'src/shortint/ciphertext/common.rs':[(35,145)],
 'src/shortint/parameters/multi_bit/mod.rs':[(110,142)],
 'src/shortint/parameters/multi_bit/p_fail_2_minus_64/ks_pbs.rs':[(952,992)],
 'src/shortint/parameters/mod.rs':[(775,810)],
 'src/shortint/parameters/classic/gaussian/p_fail_2_minus_64/ks_pbs.rs':[(270,312)],
 'src/shortint/engine/mod.rs':[(160,255)],
 'src/shortint/server_key/mod.rs':[(870,915),(1040,1075),(1345,1500),(1615,1650)],
 'src/shortint/server_key/bivariate_pbs.rs':[(1,60),(130,180),(288,320)],
 'src/integer/server_key/radix/neg.rs':[(90,155)],
 'src/integer/server_key/radix_parallel/add.rs':[(1,112),(395,420),(480,700),(795,870),(985,1135),(1290,1450)],
 'src/integer/server_key/radix_parallel/sub.rs':[(135,215),(280,345),(590,735)],
 'src/integer/server_key/radix_parallel/div_mod.rs':[(80,490),(750,850)],
 'src/integer/server_key/radix_parallel/scalar_shift.rs':[(525,655)],
 'src/integer/server_key/radix_parallel/scalar_comparison.rs':[(200,315)],
 'src/shortint/server_key/shift.rs':[(395,430)],
 'src/shortint/server_key/sub.rs':[(390,408)],
 'src/shortint/server_key/neg.rs':[(220,245)],
}
def main():
 p=argparse.ArgumentParser();p.add_argument('crate');a=p.parse_args();root=Path(a.crate)
 out=HERE/'library_evidence';out.mkdir(exist_ok=True)
 manifest={'crate':'tfhe','version':'0.8.7','purpose':'Exact source excerpts for the audited paths; these are implementation evidence, not a noise-tail theorem.','files':[]}
 for rel,ranges in RANGES.items():
  file=root/rel;data=file.read_bytes();lines=data.decode().splitlines()
  text=[f'TFHE-rs 0.8.7: {rel}',f'Whole-source SHA256: {hashlib.sha256(data).hexdigest()}','']
  for start,end in ranges:
   text+=['\n--- Lines %d-%d ---'%(start,end)]+[f'{i}: {lines[i-1]}' for i in range(start,min(end,len(lines))+1)]
  name=rel.replace('/','__')+'.txt';(out/name).write_text('\n'.join(text)+'\n')
  manifest['files'].append({'source':rel,'whole_source_sha256':hashlib.sha256(data).hexdigest(),'ranges':ranges,'excerpt':name})
 for licensefile in root.glob('LICENSE*'):
  if licensefile.is_file():(out/licensefile.name).write_bytes(licensefile.read_bytes())
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(f'Captured {len(manifest["files"])} pinned source excerpts.')
if __name__=='__main__':main()
