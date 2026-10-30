"""Capture only the extracted release window using PrintWindow, not desktop pixels."""

import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image
from pywinauto import Desktop

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "test-output/release"
    exe = Path(json.loads((output / "zip-verification.json").read_text(encoding="utf-8"))["extracted_exe"])
    assert exe.resolve().is_relative_to(ROOT)
    env = dict(os.environ)
    env.update(
        PYTHONHOME=str(output / "no-python"),
        PYTHONPATH="",
        PATH=os.path.join(os.environ["SystemRoot"], "System32"),
        QT_ACCESSIBILITY="1",
        TEMP=str(ROOT / ".cache/tmp"),
        TMP=str(ROOT / ".cache/tmp"),
    )
    env.pop("QT_QPA_PLATFORM", None)
    user = ctypes.WinDLL("user32", use_last_error=True)
    gdi = ctypes.WinDLL("gdi32", use_last_error=True)
    user.GetWindowDC.argtypes = [wintypes.HWND]
    user.GetWindowDC.restype = wintypes.HDC
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi.SelectObject.restype = wintypes.HANDLE
    gdi.GetBitmapBits.argtypes = [wintypes.HBITMAP, wintypes.LONG, ctypes.c_void_p]
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    process = subprocess.Popen([str(exe)], cwd=output, env=env)
    try:
        window = None
        for _ in range(100):
            for candidate in Desktop(backend="win32").windows(process=process.pid):
                if candidate.window_text().startswith("DataClean"):
                    window = Desktop(backend="uia").window(handle=candidate.handle)
                    break
            if window is not None:
                break
            time.sleep(0.15)
        assert window is not None, "Release main window did not open"
        time.sleep(1)
        for name in ["Dashboard", "Data Editor", "Merge Files", "History"]:
            button = window.child_window(title=name, control_type="CheckBox").wrapper_object()
            rect = button.rectangle()
            point = wintypes.POINT((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
            assert user.ScreenToClient(window.handle, ctypes.byref(point))
            coordinates = (point.y << 16) | (point.x & 0xFFFF)
            assert user.PostMessageW(window.handle, 0x0201, 1, coordinates)
            assert user.PostMessageW(window.handle, 0x0202, 0, coordinates)
            time.sleep(0.5)
            assert (
                window.child_window(auto_id="QApplication.MainWindow.root.topbar.pageTitle").window_text()
                == name
            )
            rect = window.rectangle()
            width, height = rect.width(), rect.height()
            dc = user.GetWindowDC(window.handle)
            memory = gdi.CreateCompatibleDC(dc)
            bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
            old = gdi.SelectObject(memory, bitmap)
            try:
                assert user.PrintWindow(window.handle, memory, 2), ctypes.get_last_error()
                buffer = ctypes.create_string_buffer(width * height * 4)
                assert gdi.GetBitmapBits(bitmap, len(buffer), buffer) == len(buffer)
                picture = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
                path = output / ("final-" + name.replace(" ", "-").lower() + ".png")
                picture.save(path)
                print(path, picture.getextrema())
            finally:
                gdi.SelectObject(memory, old)
                gdi.DeleteObject(bitmap)
                gdi.DeleteDC(memory)
                user.ReleaseDC(window.handle, dc)
        window.close()
        assert process.wait(timeout=20) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
