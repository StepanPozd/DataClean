"""Assemble notices, audit portable contents and create/verify the Windows ZIP."""

import hashlib
import importlib.metadata as metadata
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist" / "DataClean"
RELEASE = ROOT / "release"
VERSION = "1.0.0"
SECRET_PATTERNS = {
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{80,}-----END",
    "openai-key": rb"(?<!\w)sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}",
    "github-token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "aws-key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
}


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def audit(paths):
    forbidden = {
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        "test-output",
        ".pytest_cache",
        ".ruff_cache",
        "tests",
    }
    for path in paths:
        relative = path.relative_to(APP)
        if any(part.lower() in forbidden for part in relative.parts):
            raise ValueError(f"Excluded directory found in bundle: {relative}")
        if path.suffix.lower() in {".csv", ".xlsx", ".log", ".tmp", ".ps1", ".spec"}:
            raise ValueError(f"Unexpected user/build artifact: {relative}")
        if path.name.startswith(".env"):
            raise ValueError(f"Local configuration in bundle: {relative}")
        payload = path.read_bytes()
        for category, pattern in SECRET_PATTERNS.items():
            if re.search(pattern, payload):
                raise ValueError(f"Potential {category}: {relative} (value withheld)")
    for path in (ROOT / "app").rglob("*.py"):
        for category, pattern in SECRET_PATTERNS.items():
            if re.search(pattern, path.read_bytes()):
                raise ValueError(f"Potential {category} in application source (value withheld)")


def main():
    assert APP.resolve().is_relative_to(ROOT), "Distribution must remain within project"
    assert RELEASE.resolve().is_relative_to(ROOT), "Release must remain within project"
    exe = APP / "DataClean.exe"
    if not exe.is_file():
        raise FileNotFoundError("Build DataClean.exe with PyInstaller first")
    image = pefile.PE(str(exe), fast_load=True)
    assert image.FILE_HEADER.Machine == 0x8664, "Windows x64 executable required"
    assert image.OPTIONAL_HEADER.Subsystem == 2, "EXE must use Windows GUI subsystem"
    assert not image.OPTIONAL_HEADER.DATA_DIRECTORY[4].VirtualAddress, (
        "Update signing report before distributing a signed build"
    )
    license_dir = ROOT / "packaging" / "licenses"
    if not (license_dir / "UPSTREAM-SOURCES.json").is_file():
        subprocess.run([sys.executable, str(ROOT / "tools/collect_licenses.py")], cwd=ROOT, check=True)
    assert list(license_dir.rglob("LGPL-3.0*.txt")), "Missing LGPLv3 license text"
    for source, name in [
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "RELEASE_NOTES.md", "RELEASE_NOTES.md"),
        (ROOT / "packaging/PORTABLE_README.txt", "READ_ME_FIRST.txt"),
        (ROOT / "packaging/THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    ]:
        shutil.copy2(source, APP / name)
    for source in license_dir.rglob("*"):
        if not source.is_file() or any(
            part.lower() in {"tests", "examples", "testdata"}
            for part in source.relative_to(license_dir).parts
        ):
            continue
        destination = APP / "LICENSES" / source.relative_to(license_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    manifest_path = APP / "MANIFEST.sha256"
    payloads = sorted(
        (path for path in APP.rglob("*") if path.is_file() and path != manifest_path),
        key=lambda path: path.relative_to(APP).as_posix(),
    )
    audit(payloads)
    manifest = {path.relative_to(APP).as_posix(): sha256(path) for path in payloads}
    manifest_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in manifest.items()), encoding="utf-8"
    )
    paths = [*payloads, manifest_path]
    RELEASE.mkdir(exist_ok=True)
    archive = RELEASE / f"DataClean-v{VERSION}-win64.zip"
    staged = RELEASE / (archive.name + ".tmp")
    with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in paths:
            bundle.write(path, "DataClean/" + path.relative_to(APP).as_posix())
    with zipfile.ZipFile(staged) as bundle:
        assert bundle.testzip() is None, "ZIP CRC failure"
        assert len(bundle.namelist()) == len(paths)
        for name, expected in manifest.items():
            assert hashlib.sha256(bundle.read("DataClean/" + name)).hexdigest() == expected
        assert (APP / "_internal/python313.dll").is_file()
        assert bundle.read("DataClean/_internal/assets/icon.ico") == (ROOT / "assets/icon.ico").read_bytes()
    staged.replace(archive)
    archive_hash = sha256(archive)
    (RELEASE / (archive.name + ".sha256")).write_text(f"{archive_hash}  {archive.name}\n", encoding="ascii")
    info = {
        "version": VERSION,
        "python": sys.version.split()[0],
        "pyinstaller": metadata.version("pyinstaller"),
        "exe_bytes": exe.stat().st_size,
        "exe_sha256": sha256(exe),
        "zip_bytes": archive.stat().st_size,
        "zip_sha256": archive_hash,
        "distribution_bytes": sum(path.stat().st_size for path in paths),
        "file_count": len(paths),
        "archive": str(archive),
        "architecture": "AMD64",
        "console": False,
        "digitally_signed": False,
        "crc_verified": True,
        "all_manifest_hashes_verified": True,
        "secret_scan_findings": 0,
        "qt_dlls": sorted(path.name for path in APP.rglob("Qt6*.dll")),
    }
    (RELEASE / "build-info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2), flush=True)


if __name__ == "__main__":
    main()
