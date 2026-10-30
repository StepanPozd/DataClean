"""Independently check the release ZIP/manifest and extract a fresh copy for GUI QA."""

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    release = ROOT / "release"
    archive = release / "DataClean-v1.0.1-win64.zip"
    expected = archive.with_name(archive.name + ".sha256").read_text().split()[0]
    with archive.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    assert actual == expected
    target = ROOT / "test-output" / "release" / ("распакованный релиз " + uuid4().hex[:8])
    assert target.resolve().is_relative_to(ROOT)
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert len(set(names)) == len(names)
        for name in names:
            parts = PurePosixPath(name).parts
            assert parts[0] == "DataClean" and ".." not in parts and not name.startswith("/")
            assert not any(
                part in {".venv", "venv", ".git", "__pycache__", "tests", "test-output"} for part in parts
            )
        assert bundle.testzip() is None
        manifest = bundle.read("DataClean/MANIFEST.sha256").decode("utf-8")
        entries = [line.split("  ", 1) for line in manifest.splitlines()]
        assert {"DataClean/" + name for _, name in entries} | {"DataClean/MANIFEST.sha256"} == set(names)
        for expected_hash, name in entries:
            assert hashlib.sha256(bundle.read("DataClean/" + name)).hexdigest() == expected_hash
        bundle.extractall(target)
    exe = target / "DataClean" / "DataClean.exe"
    assert exe.is_file() and (exe.parent / "_internal/python313.dll").is_file()
    result = {
        "zip_sha256": actual,
        "files": len(names),
        "crc": "passed",
        "manifest": "passed",
        "extracted_exe": str(exe),
    }
    output = ROOT / "test-output/release/zip-verification.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
