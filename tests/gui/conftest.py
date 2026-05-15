"""Qt smoke-test configuration."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app() -> Iterator["QApplication"]:
    from PySide6.QtWidgets import QApplication

    app = cast("QApplication", QApplication.instance()) or QApplication([])
    yield app
    app.processEvents()
