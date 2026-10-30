"""Render actual widgets with synthetic data for reproducible visual QA."""

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from PySide6.QtCore import QTimer

    from app.core.data_manager import Snapshot
    from app.core.data_processor import merge_frames
    from app.core.file_handler import canonical, read_file
    from app.ui.main_window import MainWindow
    from main import create_application

    application = create_application([])
    window = MainWindow()
    window.resize(1340, 850)
    source = ROOT / "examples" / "customers_dirty.csv"
    started = perf_counter()
    loaded = read_file(source)
    snapshot = Snapshot.prepare(loaded.frame)
    window._import_loaded((loaded, snapshot), perf_counter() - started)
    more = read_file(ROOT / "examples" / "customers_more.csv")
    for item in [loaded, more]:
        window.merge_page.add_file(item)
        window.manager.protected_paths.add(canonical(item.path))
    started = perf_counter()
    combined = Snapshot.prepare(merge_frames([loaded.frame, more.frame]))
    window.merge_page.set_result(combined)
    window.history.add("Merge files", combined.stats.rows, "Combined 2 files.", perf_counter() - started)
    window._refresh()
    window.show()
    output = ROOT / "assets"
    output.mkdir(exist_ok=True)

    def capture():
        for index, name in enumerate(["dashboard", "editor", "merge", "history"]):
            window.navigate(index)
            application.processEvents()
            window.grab().save(str(output / f"{name}.png"))
        window.close()
        application.quit()

    QTimer.singleShot(500, capture)
    application.exec()
    print(f"Screenshots saved in {output}")


if __name__ == "__main__":
    main()
