"""Единый источник версии приложения."""

APP_NAME = "ChatList"
__version__ = "1.0.1"


def app_title() -> str:
    return f"{APP_NAME} {__version__}"


def dist_exe_name() -> str:
    return f"{APP_NAME}-{__version__}"


def installer_filename() -> str:
    return f"{APP_NAME}-Setup-{__version__}.exe"
