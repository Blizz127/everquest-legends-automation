from pathlib import Path

import pytest

from eql_automation.prior_rotation_core import Catalog, Spell
from eql_automation.spell_catalog import (
    build_spell_level_index, parse_class_names, parse_spell_levels,
)
from eql_automation.spells import SpellPlanner


def synthetic_class_names() -> str:
    names = {2: "Cleric", 3: "Paladin", 12: "Wizard"}
    return "".join(f"{i}^45^{names.get(i, f'Class{i}')}^0^\n" for i in range(1, 17))


def row(spell_id: int, name: str, levels: dict[int, int]) -> str:
    fields = ["0"] * 174
    fields[0] = str(spell_id)
    fields[1] = name
    fields[14] = "10"
    for class_id in range(1, 17):
        fields[35 + class_id] = str(levels.get(class_id, 255))
    return "^".join(fields)


def synthetic_spells() -> str:
    return "\n".join((
        row(14, "Strike", {2: 1, 3: 1}),
        row(200, "Minor Healing", {2: 1, 3: 1}),
        row(210, "Yaulp", {2: 1, 3: 9}),
        row(500, "Synthetic Wizard Spell", {12: 5}),
        row(501, "NPC Only", {}),
    )) + "\n"


def test_client_class_table_and_class_specific_spell_levels(tmp_path: Path):
    names = parse_class_names(synthetic_class_names())
    spells = parse_spell_levels(synthetic_spells(), names)
    assert len(names) == 16 and len(spells) == 4
    assert spells[210].level_for("Cleric") == 1
    assert spells[210].level_for("Paladin") == 9
    assert spells[500].level_for("Wizard") == 5
    assert 501 not in spells
    source = tmp_path / "client-copy"
    source.mkdir()
    (source / "dbstr_us.txt").write_text(synthetic_class_names())
    (source / "spells_us.txt").write_text(synthetic_spells())
    index, path = build_spell_level_index(source, tmp_path / "store")
    assert path.exists() and index.counts()["Paladin"] == 3
    assert index.search("Yaulp", class_name="Paladin", level=1) == []
    assert [entry.id for entry in index.search("Yaulp", class_name="Paladin", level=9)] == [210]
    with pytest.raises(ValueError, match="class is required"):
        index.search("Yaulp", level=1)
    planner = SpellPlanner.from_client_index(index)
    assert [spell.id for spell in planner.eligible({"paladin"}, 1)] == [14, 200]
    assert [spell.id for spell in planner.eligible({"paladin"}, 9)] == [14, 200, 210]
    cached, same_path = build_spell_level_index(source, tmp_path / "store")
    assert same_path == path and cached.counts() == index.counts()


def test_spell_index_rejects_bad_layout_and_duplicate_ids():
    names = parse_class_names(synthetic_class_names())
    with pytest.raises(ValueError, match="Unexpected client spell layout"):
        parse_spell_levels("14^Strike", names)
    with pytest.raises(ValueError, match="Duplicate client spell ID"):
        parse_spell_levels(synthetic_spells() + row(14, "Strike", {2: 1}), names)


def test_prior_rotation_profile_uses_the_characters_class_level():
    spells = [
        Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 0),
        Spell(200, "Minor Healing", 1, 1, 1500, 500, 0, 10, 0, 0),
        Spell(210, "Yaulp", 1, 9, 1000, 500, 0, 10, 0, 0),
    ]
    catalog = Catalog(spells)
    assert catalog.profile(1, class_name="cleric")["yaulp"].id == 210
    assert "yaulp" not in catalog.profile(1, class_name="paladin")
    assert catalog.profile(9, class_name="paladin")["yaulp"].id == 210
