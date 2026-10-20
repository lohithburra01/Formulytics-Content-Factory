"""Pydantic shapes for knowledge notes and the Weekend Pack.

Every value carries exactly one origin. ASSUMED is allowed in a NOTE only as a
migration label (the value has no known origin yet); the resolver never lets it
into a pack - it becomes a question for the user instead.
"""
from __future__ import annotations

import datetime as dt
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, model_validator

Origin = Literal["MEASURED", "COMPUTED", "FITTED", "KNOWLEDGE", "USER_DECISION"]
NoteOrigin = Union[Origin, Literal["ASSUMED"]]

# Least specific first; a later layer overrides an earlier one (grill D9).
LAYERS = ["regulations", "season", "car", "driver", "track", "weekend",
          "session", "run", "output"]

Scalar = Union[bool, int, float, str, None, list[float]]


class Value(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Scalar
    unit: str = ""
    origin: NoteOrigin
    source: Optional[str] = None       # MEASURED / COMPUTED / KNOWLEDGE / FITTED: what produced it
    reason: Optional[str] = None       # USER_DECISION: why
    decided: Optional[dt.date] = None  # USER_DECISION: when
    fit_target: Optional[str] = None   # FITTED: the feature it was tuned to
    fit_range: Optional[tuple[float, float]] = None  # FITTED: plausible range
    file: bool = False                 # value is a repo-relative path; the pack pins its sha256
    pending_review: bool = False       # no recorded reason yet: listed in the review table for the user
    note: Optional[str] = None

    @model_validator(mode="after")
    def _origin_fields(self):
        o = self.origin
        if o in ("MEASURED", "COMPUTED", "KNOWLEDGE", "FITTED") and not self.source:
            raise ValueError(f"{o} value needs a source")
        if o == "USER_DECISION" and not (self.reason and self.decided):
            raise ValueError("USER_DECISION value needs a reason and a date")
        if o == "FITTED":
            if not (self.fit_target and self.fit_range):
                raise ValueError("FITTED value needs fit_target and fit_range")
            lo, hi = self.fit_range
            if not lo <= float(self.value) <= hi:
                raise ValueError(f"FITTED value {self.value} outside its range {self.fit_range}")
        return self


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    layer: Literal[tuple(LAYERS)]  # type: ignore[valid-type]
    scope: dict[str, Union[str, int]] = {}   # empty = applies to every weekend
    links: list[str] = []
    values: dict[str, Value]


class PackValue(Value):
    origin: Origin                     # ASSUMED can never reach a pack
    layer: str
    note_id: str
    sha256: Optional[str] = None       # set for file values


class WeekendPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekend: dict[str, Union[str, int]]
    values: dict[str, PackValue]
