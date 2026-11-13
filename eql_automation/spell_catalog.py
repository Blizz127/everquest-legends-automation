"""Client-derived class levels; no server availability or vendor assumptions.

The retail client's dbstr_us.txt identifies class IDs 1–16. The paired
spells_us.txt has a 16-column class level block at fields 36–51. This layout
is checked against known Cleric and Paladin rows before it is accepted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import gzip
import json

from .client_ingest import sha256_file
from .nav import MAP_STORE


FORMAT = "client-spell-levels-v1"


@dataclass(frozen=True)
class ClientSpellLevel:
    id: int
    name: str
    mana: int
    class_levels: dict[str, int]

    def level_for(self, class_name: str) -> int | None:
        return self.class_levels.get(class_name.casefold())


@dataclass
class ClientSpellLevelIndex:
    spell_sha256: str
    class_name_sha256: str
    class_names: dict[int, str]
    spells: dict[int, ClientSpellLevel]

    def counts(self) -> dict[str, int]:
        return {name: sum(name.casefold() in spell.class_levels
                          for spell in self.spells.values())
                for name in self.class_names.values()}

    def search(self, text: str = "", *, class_name: str | None = None,
               level: int | None = None, limit: int = 20) -> list[ClientSpellLevel]:
        if limit < 1:
            raise ValueError("Limit must be positive")
        if level is not None and not 1 <= level <= 50:
            raise ValueError("Level must be 1–50")
        names = {name.casefold() for name in self.class_names.values()}
        key = class_name.casefold() if class_name else None
        if key is not None and key not in names:
            raise ValueError(f"Unknown client class: {class_name}")
        if level is not None and key is None:
            raise ValueError("A class is required when filtering by level")
        matches = []
        for spell in self.spells.values():
            if text.casefold() not in spell.name.casefold():
                continue
            unlocked = spell.class_levels.get(key) if key else None
            if key is not None and unlocked is None:
                continue
            if level is not None and unlocked > level:
                continue
            matches.append(spell)
            if len(matches) == limit:
                break
        return matches


def parse_class_names(text: str) -> dict[int, str]:
    names: dict[int, str] = {}
    for raw in text.splitlines():
        fields = raw.split("^")
        if (len(fields) < 3 or fields[1] != "45" or
                not fields[0].isdigit() or not 1 <= int(fields[0]) <= 16):
            continue
        class_id = int(fields[0])
        if class_id in names or not fields[2].strip():
            raise ValueError(f"Invalid or duplicate client class ID {class_id}")
        names[class_id] = fields[2].strip()
    if set(names) != set(range(1, 17)):
        raise ValueError("Client class-name table is incomplete")
    if names[2].casefold() != "cleric" or names[3].casefold() != "paladin":
        raise ValueError("Client class-name layout failed Cleric/Paladin check")
    return names


def parse_spell_levels(text: str, class_names: dict[int, str]) -> dict[int, ClientSpellLevel]:
    spells: dict[int, ClientSpellLevel] = {}
    sanity: dict[int, ClientSpellLevel] = {}
    seen_ids: set[int] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        fields = raw.rstrip("\r").split("^")
        if len(fields) != 174 or not fields[0].isdigit():
            raise ValueError(f"Unexpected client spell layout at line {number}")
        spell_id = int(fields[0])
        if spell_id in seen_ids:
            raise ValueError(f"Duplicate client spell ID {spell_id}")
        seen_ids.add(spell_id)
        try:
            class_levels = {
                class_names[class_id].casefold(): int(fields[35 + class_id])
                for class_id in range(1, 17)
                if 1 <= int(fields[35 + class_id]) <= 50
            }
            mana = int(fields[14])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid client spell fields at line {number}") from exc
        spell = ClientSpellLevel(spell_id, fields[1], mana, class_levels)
        if spell_id in {14, 200, 210}:
            sanity[spell_id] = spell
        if class_levels:
            spells[spell_id] = spell
    if (sanity.get(14) is None or sanity[14].name != "Strike" or
            sanity[14].level_for("cleric") != 1 or
            sanity[14].level_for("paladin") != 1 or
            sanity.get(200) is None or sanity[200].name != "Minor Healing" or
            sanity[200].level_for("cleric") != 1 or
            sanity[200].level_for("paladin") != 1 or
            sanity.get(210) is None or sanity[210].name != "Yaulp" or
            sanity[210].level_for("cleric") != 1 or
            sanity[210].level_for("paladin") != 9):
        raise ValueError("Client spell class layout failed known-row checks")
    return spells


def build_spell_level_index(source: Path, store: Path = MAP_STORE) -> tuple[ClientSpellLevelIndex, Path]:
    spell_path = source / "spells_us.txt"
    name_path = source / "dbstr_us.txt"
    if not spell_path.is_file() or not name_path.is_file():
        raise FileNotFoundError("Copied spells_us.txt or dbstr_us.txt is missing")
    spell_hash = sha256_file(spell_path)
    name_hash = sha256_file(name_path)
    index_path = store / "indices" / f"spell-levels-{spell_hash[:16]}-{name_hash[:16]}.json.gz"
    if index_path.is_file():
        with gzip.open(index_path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
        if (payload.get("format") != FORMAT or
                payload.get("spell_sha256") != spell_hash or
                payload.get("class_name_sha256") != name_hash):
            raise ValueError("Stored spell index does not match client text")
        return ClientSpellLevelIndex(
            spell_hash, name_hash,
            {int(key): value for key, value in payload["class_names"].items()},
            {entry["id"]: ClientSpellLevel(**entry) for entry in payload["spells"]}), index_path
    class_names = parse_class_names(name_path.read_text(encoding="latin-1"))
    spells = parse_spell_levels(spell_path.read_text(encoding="latin-1"), class_names)
    index = ClientSpellLevelIndex(spell_hash, name_hash, class_names, spells)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_name(index_path.name + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        json.dump({"format": FORMAT, "spell_sha256": spell_hash,
                   "class_name_sha256": name_hash, "class_names": class_names,
                   "spells": [asdict(spell) for spell in spells.values()],
                   "server_availability_verified": False,
                   "vendor_stock_verified": False}, stream, separators=(",", ":"))
    temporary.replace(index_path)
    return index, index_path
