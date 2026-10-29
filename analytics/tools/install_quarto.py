"""Quarto portatil Windows, sem alterar PATH ou instalacao global; verifica SHA-256."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

root = Path(__file__).resolve().parents[1]
lock = json.loads(Path(__file__).with_name("quarto.lock.json").read_bytes())
folder = root / ".tools"; folder.mkdir(exist_ok=True)
archive = folder / ("quarto-" + lock["version"] + "-win.zip")
if not archive.exists():
    with urllib.request.urlopen(lock["url"], timeout=90) as response, archive.open("xb") as output:
        while block := response.read(1024*1024): output.write(block)
if hashlib.sha256(archive.read_bytes()).hexdigest() != lock["sha256"]: raise ValueError("QUARTO_ARCHIVE_HASH_MISMATCH")
with zipfile.ZipFile(archive) as source:
    for member in source.infolist():
        if not (folder / member.filename).resolve().is_relative_to(folder.resolve()): raise ValueError("UNSAFE_ARCHIVE_PATH")
    source.extractall(folder)
executables = list(folder.rglob("quarto.cmd"))
if not executables: raise ValueError("QUARTO_EXECUTABLE_NOT_FOUND")
print(executables[0])
