"""Index the owner's copied default UI XML without inferring live UI state."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET

from .client_ingest import sha256_file
from .nav import MAP_STORE


UI_FILES = (
    "EQUI.xml", "EQUI_PlayerWindow.xml", "EQUI_TargetWindow.xml",
    "EQUI_CastSpellWnd.xml", "EQUI_ChatWindow.xml",
    "EQUI_InventoryWindow.xml", "EQUI_OptionsWindow.xml",
)
REQUIRED = {
    "EQUI_PlayerWindow.xml": {
        "PlayerHP": ("Gauge", "1"),
        "PlayerMana": ("Gauge", "2"),
        "ExpGauge": ("Gauge", "4"),
        "LevelLabel": ("Label", "2"),
    },
    "EQUI_TargetWindow.xml": {
        "TargetHP": ("Gauge", "6"),
        "Target_Class": ("Label", "1000"),
        "Target_Level": ("Label", "1001"),
    },
    "EQUI_ChatWindow.xml": {"CW_ChatInput": ("Editbox", "")},
    "EQUI_InventoryWindow.xml": {
        "NameLabel": ("Label", "1"),
        "LevelClassLabel": ("Label", "2"),
    },
    "EQUI_OptionsWindow.xml": {
        "OKP_KeyboardAssignmentList": ("Listbox", ""),
    },
}
REQUIRED["EQUI_CastSpellWnd.xml"] = {
    f"CSPW_Spell{index}": ("SpellGem", "") for index in range(14)
}


@dataclass(frozen=True)
class UIWidget:
    file: str
    screen_id: str
    widget_type: str
    eq_type: str


@dataclass(frozen=True)
class UISchema:
    source_sha256: dict[str, str]
    widgets: tuple[UIWidget, ...]
    active_skin_verified: bool = False
    runtime_values_verified: bool = False
    hotkeys_verified: bool = False

    def search(self, text: str, limit: int = 20) -> list[UIWidget]:
        if limit < 1:
            raise ValueError("Limit must be positive")
        query = text.casefold()
        return [widget for widget in self.widgets
                if query in widget.screen_id.casefold()][:limit]


def index_ui_widgets(source: Path, store: Path = MAP_STORE) -> tuple[UISchema, Path]:
    ui_dir = source / "uifiles" / "default"
    paths = {name: ui_dir / name for name in UI_FILES}
    if any(not path.is_file() for path in paths.values()):
        raise FileNotFoundError("Copied default UI XML files are missing")
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    widgets = []
    roots = {}
    for name, path in paths.items():
        root = ET.parse(path).getroot()
        roots[name] = root
        for element in root.iter():
            screen_id = element.findtext("ScreenID")
            if screen_id:
                widgets.append(UIWidget(name, screen_id.strip(), element.tag,
                                        (element.findtext("EQType") or "").strip()))
    included = {element.text.strip() for element in roots["EQUI.xml"].iter()
                if element.tag == "Include" and element.text}
    if not set(UI_FILES[1:]).issubset(included):
        raise ValueError("Default UI manifest does not include required windows")
    found = {(item.file, item.screen_id): (item.widget_type, item.eq_type)
             for item in widgets}
    for file, expected in REQUIRED.items():
        for screen_id, signature in expected.items():
            if found.get((file, screen_id)) != signature:
                raise ValueError(f"Client UI widget layout changed: {file}:{screen_id}")
    schema = UISchema(hashes, tuple(widgets))
    digest = sha256(json.dumps({"schema": 1, "source_sha256": hashes},
                               sort_keys=True).encode()).hexdigest()[:20]
    index_path = store / "indices" / f"ui-widgets-{digest}.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"format": "client-ui-widgets-v1",
                                     **asdict(schema)}, separators=(",", ":")) + "\n")
    temporary.replace(index_path)
    return schema, index_path
