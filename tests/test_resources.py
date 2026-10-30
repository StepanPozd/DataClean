from pathlib import Path

from app import resources
from app.ui.icons import application_icon


def test_assets_do_not_depend_on_current_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resources.resource_path("assets/icon.ico").is_file()
    assert resources.resource_path("assets/icon.png").is_file()
    assert resources.resource_path("assets/icon.svg").is_file()


def test_frozen_module_layout_resolves_internal_resources(tmp_path, monkeypatch):
    internal = tmp_path / "_internal"
    monkeypatch.setattr(resources, "__file__", str(internal / "app" / "resources.py"))
    assert resources.resource_path("assets/icon.ico") == internal / "assets" / "icon.ico"


def test_windows_icon_has_required_resolutions(qapp):
    icon = application_icon()
    assert not icon.isNull()
    sizes = {(size.width(), size.height()) for size in icon.availableSizes()}
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes
    assert Path(resources.resource_path("assets/icon.png")).stat().st_size > 0
