"""Dosya yolları.

İki tür dosya var:
- Paket kaynakları (varsayılan görseller, dil dosyası): PyInstaller ile
  paketlendiğinde geçici `_MEIPASS` klasöründe durur, salt okunurdur.
- Kullanıcı verisi (ayarlar, kullanıcının yüklediği görseller): kalıcı ve
  yazılabilir bir klasörde durmalı. Normalde EXE'nin (ya da projenin) yanı,
  orası yazılamıyorsa %APPDATA%/ScreenPet.

Görsel değiştirme ile görsel yükleme aynı `user_asset_path` fonksiyonunu
kullanır, böylece kopyalanan dosya ile okunan dosya hep aynı yerdedir.
"""

import os
import sys
import tempfile

from . import APP_NAME

SETTINGS_FILE = "ayarlar.json"
LANGUAGE_FILE = "languages.json"
USER_ASSET_FOLDER = "UserSchema"
DEFAULT_ASSET_FOLDER = "Default"

_data_dir = None


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def app_dir():
    """EXE'nin bulunduğu klasör ya da proje kökü."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundle_dir():
    """Paketlenmiş kaynakların klasörü (EXE'de geçici klasör)."""
    return getattr(sys, "_MEIPASS", app_dir())


def resource_path(relative_path):
    """Önce uygulama klasörüne (kullanıcı değiştirmiş olabilir), sonra pakete bakar."""
    for base in (app_dir(), bundle_dir()):
        candidate = os.path.join(base, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(bundle_dir(), relative_path)


def _is_writable(directory):
    try:
        os.makedirs(directory, exist_ok=True)
        fd, probe = tempfile.mkstemp(dir=directory, prefix=".write_test_")
        os.close(fd)
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir():
    """Ayarların ve kullanıcı görsellerinin tutulduğu kalıcı klasör."""
    global _data_dir
    if _data_dir is None:
        override = os.environ.get("SCREENPET_DATA_DIR")
        if override:
            _data_dir = override
        elif _is_writable(app_dir()):
            _data_dir = app_dir()
        else:
            root = os.environ.get("APPDATA") or os.path.expanduser("~")
            _data_dir = os.path.join(root, APP_NAME)
        os.makedirs(_data_dir, exist_ok=True)
    return _data_dir


def settings_path():
    return os.path.join(data_dir(), SETTINGS_FILE)


def user_asset_path(asset_type, filename):
    return os.path.join(data_dir(), "Assets", asset_type, USER_ASSET_FOLDER, filename)


def default_asset_path(asset_type, filename):
    return resource_path(os.path.join("Assets", asset_type, DEFAULT_ASSET_FOLDER, filename))


def icon_path(filename="screenpet.png"):
    return resource_path(os.path.join("Assets", "Icon", filename))
