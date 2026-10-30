"""Collect redistributable notices and exact upstream source references for the bundle.

Downloads happen only during packaging, never from the application. Archives are cached
under the project and are not placed in the end-user ZIP.
"""

import hashlib
import importlib.metadata as metadata
import json
import shutil
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "license-sources"
DEST = ROOT / "packaging" / "licenses"
RUNTIME_DISTRIBUTIONS = [
    "PySide6-Essentials",
    "shiboken6",
    "pandas",
    "numpy",
    "openpyxl",
    "charset-normalizer",
    "python-dateutil",
    "six",
    "tzdata",
    "et-xmlfile",
    "pyinstaller",
]


def retrieve(url: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    destination = CACHE / url.rsplit("/", 1)[-1]
    checksum_file = destination.with_name(destination.name + ".sha256")
    if not checksum_file.exists():
        with urllib.request.urlopen(url + ".sha256", timeout=90) as response:
            checksum_file.write_bytes(response.read())
    expected = checksum_file.read_text().split()[0].lower()
    if not destination.exists():
        temporary = destination.with_name(destination.name + ".download")
        started = monotonic()
        downloaded = temporary.stat().st_size if temporary.exists() else 0
        reported = started
        request = urllib.request.Request(url, headers={"Range": f"bytes={downloaded}-"} if downloaded else {})
        response = urllib.request.urlopen(request, timeout=30)
        if response.status != 206:
            downloaded = 0
        with response, temporary.open("ab" if downloaded else "wb") as output:
            while block := response.read1(64 * 1024):
                output.write(block)
                downloaded += len(block)
                if monotonic() - reported > 10:
                    print(f"{destination.name}: {downloaded:,} bytes", flush=True)
                    reported = monotonic()
                if monotonic() - started > 1800:
                    raise TimeoutError(f"Source download too slow: {destination.name}")
        temporary.replace(destination)
    with destination.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"Upstream archive checksum mismatch: {destination.name}")
    return destination


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    inventory = []
    for name in RUNTIME_DISTRIBUTIONS:
        distribution = metadata.distribution(name)
        license_name = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "See notices"
        )
        inventory.append({"name": name, "version": distribution.version, "license": license_name})
        for member in distribution.files or []:
            relative = Path(str(member))
            if ".dist-info" not in str(relative):
                continue
            if any(
                part.lower().startswith(("license", "copying", "notice", "authors"))
                for part in relative.parts
            ):
                source = Path(distribution.locate_file(member))
                if source.is_file():
                    target = DEST / "wheels" / name / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise FileNotFoundError("Python distribution license not found")
    shutil.copy2(python_license, DEST / "PYTHON-LICENSE.txt")
    extra_notices = {
        "OPENSSL-LICENSE.txt": "https://raw.githubusercontent.com/openssl/openssl/openssl-3.0.16/LICENSE.txt",
        "EXPAT-COPYING.txt": "https://raw.githubusercontent.com/libexpat/libexpat/R_2_7_1/expat/COPYING",
        "SQLITE-PUBLIC-DOMAIN.html": "https://www.sqlite.org/copyright.html",
        "XZ-COPYING.txt": "https://raw.githubusercontent.com/tukaani-project/xz/v5.6.4/COPYING",
    }
    for filename, url in extra_notices.items():
        path = DEST / filename
        if not path.exists():
            with urllib.request.urlopen(url, timeout=45) as response:
                path.write_bytes(response.read())
    qt_version = metadata.version("PySide6-Essentials")
    series = ".".join(qt_version.split(".")[:2])
    sources = {
        "qtbase": f"https://download.qt.io/official_releases/qt/{series}/{qt_version}/submodules/qtbase-everywhere-src-{qt_version}.tar.xz",
        "qtsvg": f"https://download.qt.io/official_releases/qt/{series}/{qt_version}/submodules/qtsvg-everywhere-src-{qt_version}.tar.xz",
        "pyside": f"https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{qt_version}-src/pyside-setup-everywhere-src-{qt_version}.tar.xz",
    }
    source_records = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        archives = dict(zip(sources, pool.map(retrieve, sources.values())))
    for component, url in sources.items():
        print(f"Collecting official {component} {qt_version} source notices…", flush=True)
        archive = archives[component]
        with archive.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        source_records.append({"component": component, "version": qt_version, "url": url, "sha256": digest})
        with tarfile.open(archive, "r:xz") as source_tar:
            for member in source_tar:
                if not member.isfile() or member.size > 300_000:
                    continue
                path = Path(member.name)
                if any(part.lower() in {"tests", "examples", "testdata"} for part in path.parts):
                    continue
                name = path.name.lower()
                wanted = (
                    name.startswith(("license", "copying", "copyright", "notice"))
                    or name == "qt_attribution.json"
                )
                wanted |= any(part.lower() == "licenses" for part in path.parts) and path.suffix in {
                    ".txt",
                    ".md",
                }
                if (
                    wanted
                    and ".." not in path.parts
                    and path.suffix not in {".cpp", ".h", ".py", ".qdoc", ".png", ".svg"}
                ):
                    target = DEST / "qt-source-notices" / component / Path(*path.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source_tar.extractfile(member) as handle:
                        target.write_bytes(handle.read())
    (DEST / "COMPONENTS.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (DEST / "UPSTREAM-SOURCES.json").write_text(json.dumps(source_records, indent=2), encoding="utf-8")
    assert list(DEST.rglob("LGPL-3.0*.txt")), "LGPL license text must be present"
    print(f"Collected notices under {DEST}", flush=True)


if __name__ == "__main__":
    main()
