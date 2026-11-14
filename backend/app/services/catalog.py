from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TestAlias, TestDefinition
from ..parsing import ParsedValue

BLOODLIKE = ("blood", "serum", "plasma")

# İdrarda strip (nitel) ve mikroskopi (sayısal) aynı adla gelebilir
_URINE_MICRO = {"urine.blood": "urine.micro_rbc", "urine.leukocyte_esterase": "urine.micro_wbc"}
_RE_RANGE_TEXT = re.compile(r"^\d+\s*[-–]\s*\d+$")


def specimen_group(specimen: str | None) -> list[str]:
    if specimen in BLOODLIKE:
        return [specimen, *[s for s in BLOODLIKE if s != specimen]]
    if specimen:
        return [specimen]
    return ["serum", "blood", "plasma", "urine", "other"]


class CatalogResolver:
    """Bir istek boyunca katalogu bellekte tutar."""

    def __init__(self, db: Session):
        self.db = db
        self.defs_by_id: dict[str, TestDefinition] = {}
        self.defs_by_key: dict[str, TestDefinition] = {}
        for d in db.scalars(select(TestDefinition)):
            self.defs_by_id[d.id] = d
            self.defs_by_key[d.key] = d
        self.aliases: dict[tuple[str, str], str] = {
            (a.alias_normalized, a.specimen): a.test_definition_id for a in db.scalars(select(TestAlias))
        }

    def by_key(self, key: str | None) -> TestDefinition | None:
        return self.defs_by_key.get(key) if key else None

    def resolve(self, alias_key: str, specimen: str | None, value: ParsedValue) -> TestDefinition | None:
        td = None
        for sp in specimen_group(specimen):
            tid = self.aliases.get((alias_key, sp))
            if tid:
                td = self.defs_by_id.get(tid)
                break
        if td is not None and td.key in _URINE_MICRO:
            is_numeric_only = value.value_numeric is not None and not value.value_text
            is_range_text = bool(value.value_text and _RE_RANGE_TEXT.match(value.value_text))
            if is_numeric_only or is_range_text:
                td = self.defs_by_key.get(_URINE_MICRO[td.key], td)
        return td
