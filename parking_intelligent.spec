# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from importlib.util import find_spec

from PyInstaller.utils.hooks import collect_all, collect_data_files


project_dir = Path(SPECPATH).resolve()
datas = [
    (str(project_dir / "models"), "models"),
    (str(project_dir / "test-video"), "test-video"),
]
binaries = []
hiddenimports = []

for package in ("easyocr", "tkinter_icons", "torchvision"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

torchvision_spec = find_spec("torchvision")
if torchvision_spec is None or torchvision_spec.origin is None:
    raise RuntimeError("TorchVision is required to package EasyOCR.")
torchvision_dir = Path(torchvision_spec.origin).parent
binaries += [
    (str(extension), "torchvision")
    for extension in torchvision_dir.glob("*.pyd")
]

datas += collect_data_files("tzdata")

analysis = Analysis(
    [str(project_dir / "run.py")],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="ParkingIntelligent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
