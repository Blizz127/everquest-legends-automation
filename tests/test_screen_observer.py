from PIL import Image
import pytest

from eql_automation.prior_rotation_core import bar_fraction
from eql_automation.screen_observer import (
    GaugeCalibration, GaugeReader, XpGaugeCalibration, XpGaugeReader,
)
from eql_automation.assist import AssistObservation, TargetRelation


def full_frame() -> Image.Image:
    frame = Image.new("RGB", (120, 30), (20, 20, 20))
    frame.paste((200, 20, 20), (0, 0, 100, 8))
    frame.paste((20, 20, 200), (0, 12, 100, 20))
    # Red elsewhere is not evidence that the player HP crop is valid.
    frame.paste((200, 20, 20), (110, 0, 120, 8))
    return frame


def calibration(frame: Image.Image) -> GaugeCalibration:
    return GaugeCalibration.from_full_frame(
        frame, hp_box=(0, 0, 100, 8), mana_box=(0, 12, 100, 20),
        layout_fingerprint="synthetic-default-skin")


def test_calibrated_gauges_read_half_hp_and_full_mana():
    full = full_frame()
    reader = GaugeReader(calibration(full))
    half = full.copy()
    half.paste((20, 20, 20), (50, 0, 100, 8))
    reading = reader.read(half, observed_at=10.0, focused_game_window=True,
                          layout_fingerprint="synthetic-default-skin")
    assert reading.complete and reading.reason is None
    assert reading.hp == 0.5 and reading.mana == 1.0
    assist = AssistObservation.from_gauges(
        reading, character_name="SyntheticTester", class_name="Paladin",
        level=1, game_focused=True, chat_open=False,
        current_target_verified=True,
        target_token="synthetic-target-selection-1",
        memorized={1: 200, 3: 14})
    assert assist.observed_at == 10.0 and assist.hp == 0.5 and assist.mana == 1.0
    assert assist.target_relation == TargetRelation.UNKNOWN


def test_gauge_reader_fails_closed_on_focus_layout_size_or_empty_bar():
    full = full_frame()
    reader = GaugeReader(calibration(full))
    def read(image, *, focus=True, layout="synthetic-default-skin"):
        return reader.read(image, observed_at=10.0, focused_game_window=focus,
                           layout_fingerprint=layout)
    assert not read(full, focus=False).complete
    assert not read(full, layout="changed-skin").complete
    assert not read(full.resize((121, 30))).complete
    empty = full.copy()
    empty.paste((20, 20, 20), (0, 0, 100, 8))
    assert read(empty).hp is None  # Zero-looking fill cannot be distinguished from invalid.


def test_calibration_requires_full_distinct_inner_bars_and_valid_channel():
    frame = full_frame()
    half = frame.copy()
    half.paste((20, 20, 20), (50, 0, 100, 8))
    with pytest.raises(ValueError, match="visibly full"):
        calibration(half)
    with pytest.raises(ValueError, match="overlap"):
        GaugeCalibration.from_full_frame(
            frame, hp_box=(0, 0, 100, 8), mana_box=(0, 4, 100, 20),
            layout_fingerprint="synthetic-default-skin")
    with pytest.raises(ValueError, match="channel"):
        bar_fraction(frame.crop((0, 0, 100, 8)), "green")


def xp_frame(percent: int) -> Image.Image:
    frame = Image.new("RGB", (120, 46), (20, 20, 20))
    frame.paste((220, 150, 0), (0, 24, percent, 32))
    frame.paste((51, 150, 51), (0, 36, 100, 44))  # Separate AA gauge.
    for x in range(10, percent, 10):
        frame.paste((0, 80, 220), (x, 24, min(x + 2, percent), 32))
    return frame


def test_xp_reader_requires_same_frame_label_calibration_and_correct_crop():
    reference = xp_frame(50)
    calibration = XpGaugeCalibration.from_reference_frame(
        reference, xp_box=(0, 24, 100, 32),
        layout_fingerprint="synthetic-default-skin", displayed_percent=50)
    reader = XpGaugeReader(calibration)
    quarter = reader.read(xp_frame(25), observed_at=20,
                          focused_game_window=True,
                          layout_fingerprint="synthetic-default-skin",
                          displayed_percent=25)
    assert quarter.level_fraction == 0.25 and quarter.reason is None
    assert reader.read(xp_frame(25), observed_at=20.1,
                       focused_game_window=True,
                       layout_fingerprint="synthetic-default-skin",
                       displayed_percent=80).level_fraction is None
    with pytest.raises(ValueError, match="does not match"):
        XpGaugeCalibration.from_reference_frame(
            reference, xp_box=(0, 24, 100, 32),
            layout_fingerprint="synthetic-default-skin", displayed_percent=80)
    with pytest.raises(ValueError, match="does not match"):
        XpGaugeCalibration.from_reference_frame(
            reference, xp_box=(0, 36, 100, 44),
            layout_fingerprint="synthetic-default-skin", displayed_percent=50)


def test_xp_reader_fails_closed_on_unknown_or_changed_capture():
    calibration = XpGaugeCalibration.from_reference_frame(
        xp_frame(50), xp_box=(0, 24, 100, 32),
        layout_fingerprint="synthetic-default-skin", displayed_percent=50)
    reader = XpGaugeReader(calibration)
    def read(frame, *, focus=True, layout="synthetic-default-skin"):
        return reader.read(frame, observed_at=20,
                           focused_game_window=focus, layout_fingerprint=layout)
    assert read(xp_frame(25), focus=False).level_fraction is None
    assert read(xp_frame(25), layout="changed-skin").level_fraction is None
    assert read(xp_frame(25).resize((121, 46))).level_fraction is None
    assert read(xp_frame(0)).level_fraction is None
