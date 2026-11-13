import json
from pathlib import Path

from tools.summarize_owner_nov12_trace import summarize


def test_g0_summary_reports_motion_without_leaking_locations(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    rows = [
        {"event": "ap_stop_check_fix", "stage": "preflight_first",
         "loc": [12.0, 34.0, 56.0], "time": 1000},
        {"event": "ap_stop_check_fix", "stage": "post_release_second",
         "loc": [13.0, 35.0, 56.0], "time": 1001},
        {"event": "ap_stop_check_result", "outcome": "observed_stop",
         "held": 0.15, "displacement": 1.25, "final_displacement": 1.26,
         "post_release_xy": 0.01, "post_release_z": 0.0, "time": 1002},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    result = summarize(path)

    assert result["g0_trace_outcomes"] == {"observed_stop": 1}
    assert result["g0_fix_stages"] == {
        "post_release_second": 1, "preflight_first": 1}
    assert result["g0_last_trace_result"]["held_seconds"] == 0.15
    assert result["g0_last_trace_result"]["displacement"] == 1.25
    assert result["g0_last_trace_result"]["post_release_xy"] == 0.01
    assert result["owner_visual_stop_confirmed"] is None
    assert "loc" not in json.dumps(result)


def test_g0_summary_rejects_nonfinite_motion_values(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    path.write_text(json.dumps({"event": "ap_stop_check_result",
                                "outcome": "failed", "reason": "still moving",
                                "held": True, "displacement": float("nan"),
                                "post_release_xy": -1}) + "\n")

    result = summarize(path)

    assert result["g0_trace_outcomes"] == {"failed": 1}
    assert result["g0_last_trace_result"]["held_seconds"] is None
    assert result["g0_last_trace_result"]["displacement"] is None
    assert result["g0_last_trace_result"]["post_release_xy"] is None
