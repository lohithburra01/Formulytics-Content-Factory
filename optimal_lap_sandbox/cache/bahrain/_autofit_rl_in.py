"""Run cache/_autofit_2026.py unchanged, but every sim gets --raceline-in <fixed line> (min-time line).
  python cache/bahrain/_autofit_rl_in.py <raceline.json> --track bahrain"""
import os, sys
RL = os.path.abspath(sys.argv.pop(1))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache"))
import subprocess, _autofit_2026 as A
_run = subprocess.run
def run(cmd, *a, **k):
    if isinstance(cmd, list) and cmd[1:2] == [A.SIM]: cmd = cmd + ["--raceline-in", RL]
    return _run(cmd, *a, **k)
A.subprocess.run = run
sys.argv[0] = A.__file__; A.main()
