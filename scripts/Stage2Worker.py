"""Fixed isolated bootstrap; source-disabled, no activation command-line switch."""
from pathlib import Path
import sys

LIVE_BOOTSTRAP_ENABLED = False

def main():
    if LIVE_BOOTSTRAP_ENABLED is not True:
        raise SystemExit('Stage 2 worker live entry disabled')
    # Parent pins this bootstrap and every required package byte under retained
    # owner-only/non-reparse/read locks before starting the isolated interpreter.
    if len(sys.argv)!=3 or sys.argv[1]!='--stage2-worker':raise SystemExit('Fixed worker request required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))
    from mayor_updates.worker_ipc import worker_entry
    worker_entry(sys.argv[2])  # separately source-disabled even after bootstrap gate

if __name__=='__main__':main()
