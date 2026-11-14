"""Immediate, read-only UI crop writer using a caller-owned game window gate.

No input, delays, display ownership or live-state inference. The owner invokes
collection; saved UI layout is a crop proposal, never a live safety permit.
"""
from datetime import datetime, timezone
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import time

from .prepared_ui_layout import PreparedLayoutView

DEFAULT_OUTPUT = Path.home() / ".local/share/eql-automation/g2-ui-observations"
WINDOWS = ("PlayerWindow", "TargetWindow", "MainChat", "MapViewWnd")
CONTROLS = (
    ("PlayerWindow", "Player_HP"),
    ("PlayerWindow", "Player_Mana"),
    ("PlayerWindow", "PW_CombatStateAnim"),
    ("TargetWindow", "Target_HP"),
    ("TargetWindow", "Target_Class"),
    ("TargetWindow", "Target_Level"),
    ("MapViewWnd", "MRA_ZoneLabel"),
)


def file_sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def box_of(rect, image) -> tuple[int, int, int, int] | None:
    if rect is None or not all(isinstance(n, int) for n in
                               (rect.x, rect.y, rect.w, rect.h)):
        return None
    box = (rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)
    if rect.w <= 0 or rect.h <= 0 or not (0 <= box[0] < box[2] <= image.width and
                                          0 <= box[1] < box[3] <= image.height):
        return None
    return box


def validate_request(label, character, server, output, private_root):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", label):
        raise ValueError("Invalid observation label")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value)
               for value in (character, server)):
        raise ValueError("Invalid character/server identifier")
    protected = (Path.home() / "Games/everquest-legends").resolve()
    if (private_root.resolve().is_relative_to(protected)
            or not output.resolve().is_relative_to(private_root.resolve())):
        raise ValueError("Output must stay in the private G2 UI observation store")


@dataclass(frozen=True)
class UiFrameSample:
    """One borrowed-gate frame and its source-proposed regions, never a permit.

    Keep this ephemeral. The image/layout are caller-owned Python objects;
    callers must not mutate them while consuming the sample.
    """
    image: object
    layout: object
    boxes: dict
    sources: dict
    source_paths: frozenset
    metadata: dict
    source_verifier: object = None

    def check_sources(self):
        current=(self.source_verifier() if self.source_verifier is not None else
                 {str(p):file_sha(p) for p in self.source_paths if p.is_file()})
        if self.sources != current:
            raise RuntimeError("Client UI files changed while observing the frame")


def sample_focused_ui(*, gate, layout_loader, game, character, server,
                      include_chat=False, still_current=lambda: None, clock=time.monotonic):
    """Capture once and resolve regions in memory, without writing PNG/JSON.

    Uses only the supplied gate's read methods; it neither owns nor closes it.
    Source hashes describe files after capture, not proven active runtime UI.
    """
    if not all(isinstance(v,str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}",v)
               for v in (character,server)):
        raise ValueError("Invalid character/server identifier")
    game=Path(game)
    sample_started=clock()
    still_current()
    windows = gate.windows()
    focused = gate.focused_window()
    session = gate.game_session()
    if len(windows) != 1 or focused is None or focused.id != windows[0].id or session is None:
        raise RuntimeError("Exactly one focused EverQuest window and process are required")
    capture_started_utc = datetime.now(timezone.utc).isoformat()
    capture_started_monotonic = clock()
    image = gate.capture()
    capture_ended_monotonic = clock()
    capture_ended_utc = datetime.now(timezone.utc).isoformat()
    still_current()
    final_focus = gate.focused_window()
    if (final_focus is None or final_focus.id != focused.id or
            gate.game_session() != session):
        raise RuntimeError("Game focus or process changed during capture")
    layout_started=clock()
    layout = layout_loader(game, character, server,
                           width=image.width, height=image.height)
    crops = {}
    for name in WINDOWS:
        if name == "MainChat" and not include_chat:
            continue
        crops[name] = box_of(layout.window(name), image)
    for window, control in CONTROLS:
        crops[f"{window}__{control}"] = box_of(layout.control(window, control), image)
    if crops["PlayerWindow__Player_HP"] is None:
        raise RuntimeError("Current client files did not resolve the player HP rectangle")
    if not any(crops.get(name) is not None for name in WINDOWS):
        raise RuntimeError("Current client files did not resolve an on-screen window")

    ini_exact = game / f"UI_{character}_{server}.ini"
    ui_ini = [ini_exact] if ini_exact.is_file() else sorted(game.glob(f"UI_{character}_{server}_*.ini"))
    source_verifier=None
    if isinstance(layout,PreparedLayoutView):
        # The cache already checked this complete dependency set after capture.
        # Keep its verifier for the end of the same feature pass, including
        # manifests and overlays omitted by ordinary layout.sources.
        sources=dict(layout.source_hashes)
        source_paths={Path(path) for path in sources}
        source_verifier=layout.source_verifier
    else:
        source_paths = {game / "eqclient.ini", *layout.sources.values(), *ui_ini}
        sources = {str(path): file_sha(path) for path in source_paths if path.is_file()}
    still_current()
    final_focus = gate.focused_window()
    if (final_focus is None or final_focus.id != focused.id or
            gate.game_session() != session):
        raise RuntimeError("Game focus or process changed during layout observation")
    metadata = {
        "capture_started_utc": capture_started_utc,
        "capture_ended_utc": capture_ended_utc,
        "capture_started_monotonic": capture_started_monotonic,
        "capture_ended_monotonic": capture_ended_monotonic,
        "capture_duration_monotonic_seconds": capture_ended_monotonic - capture_started_monotonic,
        "sample_started_monotonic": sample_started,
        "layout_started_monotonic": layout_started,
        "game_session": dict(session),
        "focused_window_id": focused.id,
        "window_size": list(image.size),
        "frame_rgb_sha256": sha256(image.tobytes()).hexdigest(),
        "ui_skin_from_saved_ini": layout.skin,
        "ui_scale_from_saved_ini": layout.ui_scale,
        "source_sha256_postcapture": sources,
        "combat_widget_source": (
            {"file": str(layout.sources["PW_CombatStateAnim"]),
             "sha256": sources.get(str(layout.sources["PW_CombatStateAnim"]))}
            if "PW_CombatStateAnim" in layout.sources else None),
        "saved_layout_is_live_verified": False,
        "map_label_is_current_zone_verified": False,
        "map_label_requires_current_zone_selection": True,
        "missing_or_offscreen_crops": [name for name, box in crops.items() if box is None],
    }
    if isinstance(layout,PreparedLayoutView):
        metadata['layout_preparation']=dict(layout.preparation)
    metadata["sample_finished_monotonic"]=clock()
    return UiFrameSample(image,layout,crops,sources,frozenset(source_paths),metadata,source_verifier)


def capture_focused_ui(*, label, gate, layout_loader, game, character, server,
                       output, include_chat=False, private_root=DEFAULT_OUTPUT,
                       still_current=lambda: None, clock=time.monotonic):
    validate_request(label, character, server, output, private_root)
    sample=sample_focused_ui(gate=gate,layout_loader=layout_loader,game=game,
        character=character,server=server,include_chat=include_chat,
        still_current=still_current,clock=clock)
    image,crops=sample.image,sample.boxes
    still_current()
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = output / f"{stamp}-{time.time_ns()}-{label}"
    dest.mkdir(mode=0o700)
    saved = {}
    for name, box in crops.items():
        if box is None:
            continue
        path = dest / f"{name}.png"
        still_current()
        image.crop(box).save(path)
        path.chmod(0o600)
        saved[name] = {"box": list(box), "file": path.name,
                       "sha256": file_sha(path)}
    sample.check_sources()
    metadata = {
        **sample.metadata,
        "format": "eql-owner-ui-observation-v1",
        "metadata_written_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner_label_unverified": label,
        "game_input_sent": False,
        "chat_crop_included": include_chat,
        "g2_safety_flags": {name: "unknown" for name in
                            ("chat_clear", "target_absent", "combat_clear",
                             "native_melee_off", "no_incoming_attack")},
        "crops": saved,
    }
    still_current()
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (dest / "metadata.json").chmod(0o600)
    print(f"Read-only private UI observation: {dest}", flush=True)
    print("All G2 safety flags remain unknown until paired live states are reviewed.", flush=True)
    return dest
