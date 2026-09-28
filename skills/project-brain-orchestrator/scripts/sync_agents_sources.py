#!/usr/bin/env python3
"""Compatibility wrapper: compile policy sources and verify generated outputs."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skill-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--source',type=Path,help='Deprecated. Edit policies/policy-catalog.json instead.')
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    if args.source:
        print('--source is deprecated: the structured policy catalog and learning ledgers are canonical',file=sys.stderr)
        return 2
    cmd=[sys.executable,str(args.skill_root/'scripts/compile_policy.py'),'--skill-root',str(args.skill_root)]
    if args.check:cmd.append('--check')
    return subprocess.run(cmd, timeout=120).returncode
if __name__=='__main__':raise SystemExit(main())
