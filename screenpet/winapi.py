"""Windows'a özel işlemler. Diğer platformlarda her fonksiyon zararsızca hiçbir şey yapmaz."""

import ctypes
import os
import sys

from . import APP_NAME, paths

IS_WINDOWS = sys.platform == "win32"

try:
    import win32api
    import win32con
    import win32gui
    HAS_PYWIN32 = IS_WINDOWS
except ImportError:
    HAS_PYWIN32 = False

try:
    import winreg
except ImportError:
    winreg = None

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_MB_ICONERROR = 0x10


def enable_dpi_awareness():
    """Pencere oluşturulmadan önce çağrılmalı.

    DPI farkında olmayan bir uygulamada Windows ekranı küçük gösterir ve pencereyi
    büyütür. %125 veya %150 ölçekte pencere ekranın tamamını kaplamaz.
    Monitör başına DPI farkındalığı ile tüm koordinatlar gerçek piksel olur.
    """
    if not IS_WINDOWS:
        return False
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4 (Windows 10 1703+)
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return True
    except (AttributeError, OSError):
        pass
    try:
        return bool(ctypes.windll.user32.SetProcessDPIAware())
    except (AttributeError, OSError):
        return False


def _monitor_scale(hmonitor):
    try:
        dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
        hr = ctypes.windll.shcore.GetDpiForMonitor(
            ctypes.c_void_p(int(hmonitor)), 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        if hr == 0 and dpi_x.value:
            return dpi_x.value / 96.0
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return system_scale()


def system_scale():
    if not IS_WINDOWS:
        return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except (AttributeError, OSError):
        return 1.0


def virtual_screen():
    """Tüm monitörleri kapsayan dikdörtgen: (x, y, genişlik, yükseklik)."""
    if not IS_WINDOWS:
        return None
    m = ctypes.windll.user32.GetSystemMetrics
    # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
    x, y, w, h = m(76), m(77), m(78), m(79)
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def monitors():
    """Monitör listesi (masaüstü koordinatlarında).

    Her öğe: {"rect": (sol, üst, sağ, alt), "work": (...), "primary": bool, "scale": float}
    "work" görev çubuğu hariç alandır.
    """
    if not HAS_PYWIN32:
        return []
    result = []
    try:
        for hmon, _hdc, _rect in win32api.EnumDisplayMonitors():
            info = win32api.GetMonitorInfo(hmon)
            result.append({
                "rect": tuple(info["Monitor"]),
                "work": tuple(info["Work"]),
                "primary": bool(info.get("Flags", 0) & 1),
                "scale": _monitor_scale(hmon),
            })
    except Exception as e:  # pywin32 farklı hata tipleri fırlatabiliyor
        print(f"Monitör bilgisi alınamadı: {e}")
        return []
    return result


def make_overlay(hwnd, key_color, bounds):
    """Pencereyi şeffaf, her zaman üstte ve görev çubuğunda görünmeyen yapar."""
    if not HAS_PYWIN32 or not hwnd:
        return False
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        # Renk anahtarına eşit pikseller görünmez olur ve tıklamalar alttaki pencereye geçer.
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*key_color), 0, win32con.LWA_COLORKEY)
        move_window(hwnd, bounds)
        return True
    except Exception as e:
        print(f"Şeffaf pencere ayarlanamadı: {e}")
        return False


def move_window(hwnd, bounds):
    if not HAS_PYWIN32 or not hwnd:
        return
    x, y, w, h = bounds
    try:
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x, y, w, h, win32con.SWP_NOACTIVATE)
    except Exception as e:
        print(f"Pencere konumlandırılamadı: {e}")


def show_window(hwnd, visible):
    if not HAS_PYWIN32 or not hwnd:
        return
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE if visible else win32con.SW_HIDE)
        if visible:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
    except Exception as e:
        print(f"Pencere gösterilemedi/gizlenemedi: {e}")


def message_box(title, message, error=False):
    if IS_WINDOWS:
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, _MB_ICONERROR if error else 0)
            return
        except (AttributeError, OSError):
            pass
    print(f"[{title}] {message}")


def startup_command():
    """Windows açılışında çalıştırılacak komut."""
    if paths.is_frozen():
        return f'"{os.path.abspath(sys.executable)}"'
    python = sys.executable
    pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
    if os.path.exists(pythonw):
        python = pythonw
    script = os.path.join(paths.app_dir(), "start.py")
    return f'"{python}" "{script}"'


def set_startup(enable):
    """Windows ile başlatma kaydını ekler veya siler. Başarılıysa True döner."""
    if not IS_WINDOWS or winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as e:
        print(f"Başlangıç kaydı değiştirilemedi: {e}")
        return False


def startup_entry():
    """Kayıtlı başlangıç komutu, yoksa None."""
    if not IS_WINDOWS or winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value
    except OSError:
        return None
