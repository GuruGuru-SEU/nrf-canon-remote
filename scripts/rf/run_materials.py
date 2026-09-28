"""Reproduce the eight material runs, preserving each solver log.

Do not run this while a named run is already active; each name owns one
tmp/rf directory. The default is sequential to bound memory and CPU use.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "reference/rf/materials-20260928.json").read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--only", nargs="+", help="Run only these material IDs (e.g. np140f ny2140-rc55)")
parser.add_argument("--state", choices=["bare", "housed", "both"], default="both")
parser.add_argument("--threads", type=int, default=4)
args = parser.parse_args()
states = ["bare", "housed"] if args.state == "both" else [args.state]
cases = []
for material in MANIFEST["materials"]:
    for case in material.get("resin_cases", [material]):
        cases.append((case, material["explanation"]))
if args.only:
    unknown = set(args.only) - {case["id"] for case, _ in cases}
    if unknown:
        parser.error(f"Unknown material IDs: {sorted(unknown)}")
(ROOT / "tmp").mkdir(exist_ok=True)
for case, note in cases:
    if args.only and case["id"] not in args.only:
        continue
    for state in states:
        name = case["id"] + "-" + state
        command = [sys.executable, "scripts/rf/simulate.py", "--name", name,
                   "--mesh", "0.1", "--thickness", "1.6", "--threads", str(args.threads),
                   "--eps", str(case["eps_r"]), "--loss", str(case["tan_delta"]),
                   "--material-note", note]
        if state == "housed":
            command += ["--shell-eps", "2.8"]
        print("Running", name, flush=True)
        with (ROOT / "tmp" / f"rf-{name}.log").open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        print("Completed", name, flush=True)
