"""Read-only HP rectangle proposal for the owner's calibration dialog.

Saved UI placement can differ from the live window. This only proposes a box;
the existing pixel preview and the owner's Save are still required. It never
changes settings or enables healing.
"""
from __future__ import annotations

from pathlib import Path
import re


def propose_hp_box(game_dir, character: str, server: str,
                   window_size: tuple[int, int], *, layout_loader=None) -> tuple[int, int, int, int]:
    if (not isinstance(character, str) or not isinstance(server, str) or
            re.fullmatch(r"[A-Za-z0-9_]{1,48}", character) is None or
            re.fullmatch(r"[A-Za-z0-9_]{1,48}", server) is None):
        raise ValueError("Select a character and server before finding the HP gauge")
    if (not isinstance(window_size, tuple) or len(window_size) != 2 or
            any(not isinstance(value, int) or isinstance(value, bool) or
                not 320 <= value <= 7680 for value in window_size)):
        raise ValueError("The captured game window has an unsupported size")
    if layout_loader is None:
        from uilayout import UiLayout, UiLayoutError
        try:
            return propose_hp_box(game_dir, character, server, window_size,
                                  layout_loader=UiLayout.load)
        except UiLayoutError as error:
            raise ValueError(f"Saved client UI layout is unavailable: {error}") from error
    width, height = window_size
    layout = layout_loader(Path(game_dir), character, server, width=width, height=height)
    if layout.visible("PlayerWindow") is False or layout.minimized("PlayerWindow") is True:
        raise ValueError("The saved player window is hidden or minimized")
    rect = layout.control("PlayerWindow", "Player_HP")
    if rect is None:
        raise ValueError("The saved client layout does not identify a player HP gauge")
    coords = (rect.x, rect.y, rect.w, rect.h)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in coords):
        raise ValueError("The saved player HP rectangle has invalid coordinates")
    x, y, w, h = coords
    if not (20 <= w <= width and 5 <= h <= 24 and
            0 <= x < x + w <= width and 0 <= y < y + h <= height):
        raise ValueError("The saved player HP rectangle is outside the narrow gauge bounds")
    return x, y, x + w, y + h
