from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from eql_automation.ui_schema import REQUIRED, UI_FILES, index_ui_widgets


def copied_ui_fixture(source: Path) -> None:
    directory = source / "uifiles" / "default"
    directory.mkdir(parents=True)
    manifest = ET.Element("XML")
    for filename in UI_FILES[1:]:
        ET.SubElement(manifest, "Include").text = filename
    ET.ElementTree(manifest).write(directory / "EQUI.xml")
    for filename in UI_FILES[1:]:
        root = ET.Element("XML")
        for screen_id, (widget_type, eq_type) in REQUIRED.get(filename, {}).items():
            element = ET.SubElement(root, widget_type)
            ET.SubElement(element, "ScreenID").text = screen_id
            if eq_type:
                ET.SubElement(element, "EQType").text = eq_type
        ET.ElementTree(root).write(directory / filename)


def test_client_ui_index_keeps_static_widget_evidence_unverified(tmp_path: Path):
    source = tmp_path / "copied-client"
    copied_ui_fixture(source)
    schema, path = index_ui_widgets(source, tmp_path / "store")
    assert path.exists()
    assert not schema.active_skin_verified
    assert not schema.runtime_values_verified
    assert not schema.hotkeys_verified
    assert [item.screen_id for item in schema.search("PlayerHP")] == ["PlayerHP"]
    assert len(schema.search("CSPW_Spell", 20)) == 14


def test_client_ui_index_rejects_changed_required_widget(tmp_path: Path):
    source = tmp_path / "copied-client"
    copied_ui_fixture(source)
    target = source / "uifiles" / "default" / "EQUI_PlayerWindow.xml"
    target.write_text(target.read_text().replace("PlayerHP", "ChangedHP"))
    with pytest.raises(ValueError, match="Client UI widget layout changed"):
        index_ui_widgets(source, tmp_path / "store")
