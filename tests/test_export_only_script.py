import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_only_runs_against_a_raw_folder(tmp_path):
    raw = tmp_path / "raw" / "Sample"
    raw.mkdir(parents=True)
    for p in FIXTURE.rglob("*"):
        if p.is_file():
            dest = raw / p.relative_to(FIXTURE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())

    exported = tmp_path / "exported"
    cmd = [sys.executable, str(REPO / "scripts" / "export_only.py"),
           "--name", "Sample",
           "--raw-root", str(tmp_path / "raw"),
           "--exported-root", str(exported),
           "--format", "csv", "--format", "markdown"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    out_dir = exported / "Sample"
    assert (out_dir / "Sample.csv").exists()
    assert (out_dir / "Sample.zip").exists()
