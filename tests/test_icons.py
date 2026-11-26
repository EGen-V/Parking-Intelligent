"""Tests for the centralized Lucide icon map."""

from __future__ import annotations

import pytest
from tkinter_icons import LucideIcon

from src.ui import icons


@pytest.mark.parametrize("name,glyph", sorted(icons._ICON_NAMES.items()))
def test_icon_mapping_uses_a_valid_lucide_glyph(name: str, glyph: str) -> None:
    icon = LucideIcon(glyph, size=20, color="#ffffff")
    assert icon.name


def test_get_icon_rejects_unknown_alias() -> None:
    with pytest.raises(ValueError, match="Unknown UI icon"):
        icons.get_icon("unknown", 16, "#ffffff")


def test_get_icon_caches_rendered_image(monkeypatch: pytest.MonkeyPatch) -> None:
    images: list[object] = []

    class FakeIcon:
        def __init__(self, glyph: str, size: int, color: str) -> None:
            self.image = object()
            images.append(self.image)

    monkeypatch.setattr(icons, "LucideIcon", FakeIcon)
    icons.clear_icon_cache()
    try:
        first = icons.get_icon("dashboard", 20, "#ffffff")
        second = icons.get_icon("dashboard", 20, "#ffffff")
        assert first is second
        assert len(images) == 1
    finally:
        icons.clear_icon_cache()
