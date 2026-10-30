"""Record reproducible CI metadata and isolate pytest groups without hiding failures."""

import argparse
import gc
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ["tests/test_processing.py", "tests/test_files.py", "tests/test_data_safety.py"]
GUI = [
    "tests/test_resources.py",
    "tests/test_ui.py",
    "tests/test_data_safety_ui.py",
    "tests/test_worker_lifetime.py",
]
GROUPS = {
    "full": ["tests"],
    "core": CORE,
    "gui": GUI,
    "excel": ["tests/test_ui.py::test_excel_import_selects_chosen_sheet"],
}


def environment():
    from PySide6 import QtCore

    packages = {item.metadata["Name"]: item.version for item in metadata.distributions()}
    return {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "qt_runtime": QtCore.qVersion(),
        "pyside": QtCore.__version__,
        "core_versions": {
            name: metadata.version(package)
            for name, package in {
                "PySide6": "PySide6-Essentials",
                "shiboken6": "shiboken6",
                "pandas": "pandas",
                "openpyxl": "openpyxl",
                "pytest": "pytest",
                "pytest-qt": "pytest-qt",
            }.items()
        },
        "packages": dict(sorted(packages.items(), key=lambda pair: pair[0].lower())),
        "gc_enabled": gc.isenabled(),
        "gc_thresholds": gc.get_threshold(),
        "switch_interval": sys.getswitchinterval(),
        "cpu_count": os.cpu_count(),
        "runner": {
            key: os.environ[key]
            for key in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")
            if key in os.environ
        },
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "offscreen"),
        "python_hash_seed": os.environ.get("PYTHONHASHSEED", "random"),
    }


def output_directory(value):
    path = value.resolve()
    if not path.is_relative_to(ROOT / "test-output"):
        raise ValueError("CI evidence must stay under project test-output")
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_tests(group, repeat, output, journal):
    known = {ROOT / path for path in CORE + GUI}
    if known != set((ROOT / "tests").glob("test_*.py")):
        raise ValueError("Update CORE/GUI groups to cover every test module")
    results = []
    child_env = dict(os.environ)
    child_env.setdefault("QT_QPA_PLATFORM", "offscreen")
    child_env.setdefault("PYTEST_QT_API", "pyside6")
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "tools"), str(ROOT)])
    for iteration in range(1, repeat + 1):
        prefix = f"{group}-{iteration:02d}"
        command = [
            sys.executable,
            "-X",
            "faulthandler",
            "-m",
            "pytest",
            "-v",
            *GROUPS[group],
            "--basetemp=" + str(output / (prefix + "-tmp")),
            "--junitxml=" + str(output / (prefix + ".xml")),
        ]
        if journal:
            command.extend(
                ["-p", "qt_diagnostics", "--qt-diagnostic-log=" + str(output / (prefix + "-events.jsonl"))]
            )
        with (output / (prefix + ".log")).open("w", encoding="utf-8") as handle:
            try:
                result = subprocess.run(
                    command, cwd=ROOT, env=child_env, stdout=handle, stderr=subprocess.STDOUT, timeout=180
                )
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                exit_code = 124
                handle.write("\nDiagnostic subprocess timed out after 180 seconds.\n")
        item = {"group": group, "iteration": iteration, "exit_code": exit_code, "journal": journal}
        results.append(item)
        (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print((output / (prefix + ".log")).read_text(encoding="utf-8", errors="replace"), flush=True)
        print(json.dumps(item), flush=True)
    return 1 if any(item["exit_code"] for item in results) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group", choices=GROUPS)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--journal", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.repeat <= 20:
        parser.error("repeat must be between 1 and 20")
    output = output_directory(args.output)
    info = environment()
    (output / "environment.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2), flush=True)
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], capture_output=True, text=True)
    (output / "freeze.txt").write_text(
        freeze.stdout
        if freeze.returncode == 0
        else "\n".join(f"{k}=={v}" for k, v in info["packages"].items()) + "\n",
        encoding="utf-8",
    )
    return run_tests(args.group, args.repeat, output, args.journal) if args.group else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
