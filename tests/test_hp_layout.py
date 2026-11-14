from types import SimpleNamespace

import pytest

from eql_automation.hp_layout import propose_hp_box


def loader(rect, calls, *, visible=True, minimized=False):
    def load(game, character, server, **size):
        calls.append((str(game), character, server, size))
        def control(window, item):
            assert (window, item) == ("PlayerWindow", "Player_HP")
            return rect
        return SimpleNamespace(control=control, visible=lambda name: visible,
                               minimized=lambda name: minimized)
    return load


def test_client_rectangle_uses_selected_identity_and_actual_capture_size():
    calls = []
    rect = SimpleNamespace(x=1966, y=693, w=330, h=17)
    box = propose_hp_box("/copied-client", "Legira", "freeport", (2560, 1600),
                         layout_loader=loader(rect, calls))
    assert box == (1966, 693, 2296, 710)
    assert calls == [("/copied-client", "Legira", "freeport", {"width": 2560, "height": 1600})]


@pytest.mark.parametrize("rect", [None,
    SimpleNamespace(x=1963, y=661, w=338, h=51),  # broken old saved calibration
    SimpleNamespace(x=-1, y=693, w=330, h=17),
    SimpleNamespace(x=2500, y=693, w=330, h=17),
    SimpleNamespace(x=1966, y=1590, w=330, h=17),
    SimpleNamespace(x=1966, y=693, w=19, h=17),
    SimpleNamespace(x=1966, y=693, w=330, h=True),
])
def test_missing_broad_small_offscreen_and_malformed_rectangles_refuse(rect):
    with pytest.raises(ValueError):
        propose_hp_box("/copied-client", "Legira", "freeport", (2560, 1600),
                       layout_loader=loader(rect, []))


@pytest.mark.parametrize("identity,size", [("../Legira", (2560, 1600)),
                                          ("Legira", (True, 1600)),
                                          ("Legira", (0, 1600))])
def test_bad_identity_and_capture_size_never_read_layout(identity, size):
    calls = []
    with pytest.raises(ValueError):
        propose_hp_box("/copied-client", identity, "freeport", size,
                       layout_loader=loader(None, calls))
    assert calls == []


@pytest.mark.parametrize("visible,minimized", [(False, False), (True, True)])
def test_saved_hidden_or_minimized_player_window_does_not_propose_a_box(visible, minimized):
    with pytest.raises(ValueError, match="hidden or minimized"):
        propose_hp_box("/copied-client", "Legira", "freeport", (2560, 1600),
                       layout_loader=loader(SimpleNamespace(x=1966, y=693, w=330, h=17), [],
                                            visible=visible, minimized=minimized))
