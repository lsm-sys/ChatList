"""Генерирует файл метаданных версии для PyInstaller."""

from __future__ import annotations

from pathlib import Path

from version import APP_NAME, __version__


def main() -> None:
    parts = [int(part) for part in __version__.split(".")]
    while len(parts) < 4:
        parts.append(0)
    major, minor, patch, build = parts[:4]

    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [
          StringStruct(u'FileVersion', u'{__version__}'),
          StringStruct(u'ProductVersion', u'{__version__}'),
          StringStruct(u'ProductName', u'{APP_NAME}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    Path(f"version-{__version__}.txt").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
