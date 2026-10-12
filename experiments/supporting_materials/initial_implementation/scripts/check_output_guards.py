#!/usr/bin/env python3
"""Non-computational validation: --help and refusal to overwrite released logs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
PROTECTED=ROOT/"results/revision_2026-10-10"

def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in PROTECTED.rglob("*") if p.is_file()}

def main():
    dest=PROTECTED/"runner_guard_checks"
    if dest.exists():raise SystemExit("refusing to overwrite existing guard records")
    before=hashes()
    checks=[]
    for name in ("run_plaintext.py","verify_exact.py","search_comparison.py","summarize_revision.py"):
        script=ROOT/"scripts"/name
        for args,expected in ((["--help"],0),(["--output-dir",str(PROTECTED)],2)):
            command=[sys.executable,str(script),*args]
            cp=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8",errors="replace")
            checks.append({"command":command,"exit":cp.returncode,"expected":expected,"output":cp.stdout})
            assert cp.returncode==expected,(name,cp.returncode,cp.stdout)
    if sys.platform=="win32":
        root_wsl="/mnt/"+str(ROOT)[0].lower()+str(ROOT)[2:].replace("\\","/")
        protected=root_wsl+"/results/revision_2026-10-10"
        for name in ("run_encrypted.sh","run_checked.sh","run_final_encrypted.sh","attempt_refined.sh","attempt_baselines.sh"):
            args=["unused_source",protected] if name=="attempt_baselines.sh" else [protected]
            command=["wsl","-d","Ubuntu","--","bash",root_wsl+"/scripts/"+name,*args]
            cp=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=0x08000000)
            checks.append({"command":command,"exit":cp.returncode,"expected":2,"output":cp.stdout})
            assert cp.returncode==2,(name,cp.returncode,cp.stdout)
    after=hashes()
    assert before==after,"released records changed during guard checks"
    dest.mkdir()
    (dest/"results.json").write_text(json.dumps({"checks":checks,"all_pass":True,"protected_files":len(before),
        "before_after_identical":True},indent=2)+"\n",encoding="utf-8")
    print(f"PASS {len(checks)} checks; {len(before)} released files unchanged")

if __name__=="__main__":main()
