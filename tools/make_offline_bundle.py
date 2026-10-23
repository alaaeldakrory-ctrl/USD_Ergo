"""Offline bundle for an air-gapped PC: the code (last commit) plus the Python wheels it needs, in one zip.

    python tools/make_offline_bundle.py [out_dir]     -> <out_dir>/ergo_scan_offline_<commit>.zip

On the offline PC: unzip, then  pip install --no-index --find-links <unzipped>/wheels usd-core numpy pillow
(Kit: add <unzipped>/exts to the extension search paths; Pillow installs from wheels/ by itself).
"""
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = "312"          # Kit 107+ and the usual standalone Python; pass --python=311 etc. for another


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    py = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--python=")), PY)
    out_dir = args[0] if args else os.path.join(ROOT, "build", "offline")
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], check=True, capture_output=True,
                            text=True).stdout.strip()
    stage = os.path.join(out_dir, "ergo-scan")
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    src = os.path.join(out_dir, "src.zip")
    subprocess.run(["git", "-C", ROOT, "archive", "--format=zip", "-o", src, "HEAD"], check=True)
    with zipfile.ZipFile(src) as z:
        z.extractall(stage)
    os.remove(src)
    wh = os.path.join(stage, "wheels")
    subprocess.run([sys.executable, "-m", "pip", "download", "--dest", wh, "--only-binary=:all:", "--platform",
                    "win_amd64", "--python-version", py, "--implementation", "cp", "usd-core", "numpy", "pillow",
                    "pytest"], check=True)
    zp = os.path.join(out_dir, f"ergo_scan_offline_{commit}.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(stage):
            for f in files:
                p = os.path.join(base, f)
                z.write(p, os.path.relpath(p, out_dir))
    print("->", zp, f"{os.path.getsize(zp) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
