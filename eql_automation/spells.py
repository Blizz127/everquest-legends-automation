"""Class-neutral, data-driven spell progression planning.

This is a planner only. Buying, scribing and memorizing require an authorized
live adapter and verified vendor, inventory and spellbook observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .prior_rotation_core import Catalog as PriorCatalog


@dataclass(frozen=True)
class SpellSpec:
    id: int
    name: str
    class_levels: dict[str, int]
    mana: int = 0

    def unlocks_at(self, class_name: str) -> int | None:
        return self.class_levels.get(class_name.casefold())


@dataclass(frozen=True)
class SpellTask:
    operation: str
    spell_id: int
    spell_name: str
    slot: int | None = None


class SpellPlanner:
    def __init__(self, spells: Iterable[SpellSpec]) -> None:
        entries = list(spells)
        self.spells = {entry.id: entry for entry in entries}
        if len(self.spells) != len(entries):
            raise ValueError("Duplicate spell ID")

    @classmethod
    def from_prior_catalog(cls, catalog: PriorCatalog) -> "SpellPlanner":
        """Reuse the October tool's validated Paladin/Cleric spell records."""

        result = []
        for spell in catalog.spells.values():
            levels = {}
            if 1 <= spell.cleric_level <= 50:
                levels["cleric"] = spell.cleric_level
            if 1 <= spell.paladin_level <= 50:
                levels["paladin"] = spell.paladin_level
            result.append(SpellSpec(spell.id, spell.name, levels, spell.mana))
        return cls(result)

    def eligible(self, class_names: set[str], level: int) -> list[SpellSpec]:
        if not 1 <= level <= 50:
            raise ValueError("Level must be 1–50")
        names = {name.casefold() for name in class_names}
        return [spell for spell in self.spells.values()
                if any((unlock := spell.unlocks_at(name)) is not None and unlock <= level
                       for name in names)]

    def plan(self, *, class_names: set[str], level: int,
             desired_slots: dict[int, int], learned: set[int],
             owned_scrolls: set[int], vendor_stock: set[int],
             memorized: dict[int, int]) -> list[SpellTask]:
        """Order acquire, scribe and memorize tasks without executing them."""

        eligible = {spell.id for spell in self.eligible(class_names, level)}
        if len(set(desired_slots.values())) != len(desired_slots):
            raise ValueError("A spell cannot occupy two desired slots")
        tasks = []
        for slot, spell_id in sorted(desired_slots.items()):
            if not 1 <= slot <= 8 or spell_id not in self.spells:
                raise ValueError("Unknown spell or gem slot")
            if spell_id not in eligible:
                raise ValueError(f"Spell {spell_id} is not unlocked for this class and level")
            spell = self.spells[spell_id]
            if spell_id not in learned:
                if spell_id not in owned_scrolls:
                    if spell_id not in vendor_stock:
                        tasks.append(SpellTask("unavailable", spell_id, spell.name))
                        continue
                    tasks.append(SpellTask("buy", spell_id, spell.name))
                tasks.append(SpellTask("scribe", spell_id, spell.name))
            if memorized.get(slot) != spell_id:
                tasks.append(SpellTask("memorize", spell_id, spell.name, slot))
        return tasks
