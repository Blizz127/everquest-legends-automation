"""Read calibrated player gauges from a supplied image, with no live capture.

The caller must provide a focused game-window frame and a verified active
layout fingerprint. No target, spell, class, level, or chat state is inferred
from gauge colors. An empty-looking bar is unknown without a verified label.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING

from .prior_rotation_core import bar_fraction

if TYPE_CHECKING:
    from PIL.Image import Image


Box = tuple[int, int, int, int]


@dataclass(frozen=True)
class GaugeCalibration:
    window_size: tuple[int, int]
    hp_box: Box
    mana_box: Box
    layout_fingerprint: str

    @classmethod
    def from_full_frame(cls, frame: "Image", *, hp_box: Box,
                        mana_box: Box, layout_fingerprint: str) -> "GaugeCalibration":
        """Accept only inner bars visibly at least 85% full at calibration."""
        if not layout_fingerprint.strip():
            raise ValueError("Active layout fingerprint is required")
        for box in (hp_box, mana_box):
            if (len(box) != 4 or not all(isinstance(value, int) for value in box)
                    or not (0 <= box[0] < box[2] <= frame.width and
                            0 <= box[1] < box[3] <= frame.height)):
                raise ValueError("Gauge box is outside the captured window")
        if (max(hp_box[0], mana_box[0]) < min(hp_box[2], mana_box[2]) and
                max(hp_box[1], mana_box[1]) < min(hp_box[3], mana_box[3])):
            raise ValueError("Player HP and mana crops overlap")
        hp = bar_fraction(frame.crop(hp_box), "red")
        mana = bar_fraction(frame.crop(mana_box), "blue")
        if hp is None or mana is None or hp < 0.85 or mana < 0.85:
            raise ValueError("Calibrate on visibly full player HP and mana inner bars")
        return cls(frame.size, hp_box, mana_box, layout_fingerprint)


@dataclass(frozen=True)
class GaugeReading:
    observed_at: float
    hp: float | None
    mana: float | None
    reason: str | None

    @property
    def complete(self) -> bool:
        return self.hp is not None and self.mana is not None


class GaugeReader:
    def __init__(self, calibration: GaugeCalibration) -> None:
        self.calibration = calibration

    def read(self, frame: "Image", *, observed_at: float,
             focused_game_window: bool,
             layout_fingerprint: str) -> GaugeReading:
        if not isfinite(observed_at):
            raise ValueError("Capture time must be finite")
        if not focused_game_window:
            return GaugeReading(observed_at, None, None, "game window not focused")
        if frame.size != self.calibration.window_size:
            return GaugeReading(observed_at, None, None, "window size changed")
        if layout_fingerprint != self.calibration.layout_fingerprint:
            return GaugeReading(observed_at, None, None, "active UI layout changed")
        hp = bar_fraction(frame.crop(self.calibration.hp_box), "red")
        mana = bar_fraction(frame.crop(self.calibration.mana_box), "blue")
        if hp is None or mana is None:
            return GaugeReading(observed_at, None, None, "player gauge unreadable")
        return GaugeReading(observed_at, hp, mana, None)


@dataclass(frozen=True)
class XpGaugeCalibration:
    """One active-skin XP crop matched to a same-frame numeric XP label."""

    window_size: tuple[int, int]
    xp_box: Box
    layout_fingerprint: str

    @classmethod
    def from_reference_frame(cls, frame: "Image", *, xp_box: Box,
                             layout_fingerprint: str,
                             displayed_percent: float) -> "XpGaugeCalibration":
        if not isinstance(layout_fingerprint, str) or not layout_fingerprint.strip():
            raise ValueError("Active layout fingerprint is required")
        if (not isinstance(xp_box, (tuple, list)) or len(xp_box) != 4 or
                not all(isinstance(value, int) and not isinstance(value, bool)
                        for value in xp_box) or
                not (0 <= xp_box[0] < xp_box[2] <= frame.width and
                     0 <= xp_box[1] < xp_box[3] <= frame.height)):
            raise ValueError("XP gauge box is outside the captured window")
        if (not isinstance(displayed_percent, (int, float)) or
                isinstance(displayed_percent, bool) or
                not isfinite(displayed_percent) or
                not 0 < displayed_percent <= 100):
            raise ValueError("A verified nonempty XP label percent is required")
        fraction = bar_fraction(frame.crop(xp_box), "amber")
        if fraction is None or abs(fraction - displayed_percent / 100) > 0.05:
            raise ValueError("XP crop does not match the same-frame XP label")
        return cls(frame.size, tuple(xp_box), layout_fingerprint)


@dataclass(frozen=True)
class XpGaugeReading:
    observed_at: float
    level_fraction: float | None
    reason: str | None


class XpGaugeReader:
    def __init__(self, calibration: XpGaugeCalibration) -> None:
        self.calibration = calibration

    def read(self, frame: "Image", *, observed_at: float,
             focused_game_window: bool, layout_fingerprint: str,
             displayed_percent: float | None = None) -> XpGaugeReading:
        if (not isinstance(observed_at, (int, float)) or
                isinstance(observed_at, bool) or not isfinite(observed_at)):
            raise ValueError("Capture time must be finite")
        if not focused_game_window:
            return XpGaugeReading(observed_at, None, "game window not focused")
        if frame.size != self.calibration.window_size:
            return XpGaugeReading(observed_at, None, "window size changed")
        if layout_fingerprint != self.calibration.layout_fingerprint:
            return XpGaugeReading(observed_at, None, "active UI layout changed")
        fraction = bar_fraction(frame.crop(self.calibration.xp_box), "amber")
        if fraction is None:
            return XpGaugeReading(observed_at, None, "XP gauge empty or unreadable")
        if displayed_percent is not None:
            if (not isinstance(displayed_percent, (int, float)) or
                    isinstance(displayed_percent, bool) or
                    not isfinite(displayed_percent) or
                    not 0 <= displayed_percent <= 100 or
                    abs(fraction - displayed_percent / 100) > 0.05):
                return XpGaugeReading(observed_at, None, "XP label and gauge disagree")
        return XpGaugeReading(observed_at, fraction, None)
