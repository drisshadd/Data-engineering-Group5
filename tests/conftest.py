import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))

# The tests need the generator files (seed 42, 2 batches). Create them once if missing.
if not (ROOT / "generator" / "out" / "skyhop" / "batch_002").exists():
    subprocess.run([sys.executable, str(ROOT / "generator" / "messy_data.py"), "--company", "skyhop", "--batches", "2",
                    "--seed", "42", "--out", str(ROOT / "generator" / "out")], check=True, capture_output=True)
