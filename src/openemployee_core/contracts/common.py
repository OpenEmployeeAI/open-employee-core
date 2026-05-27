"""Shared primitives for OpenEmployee Core contracts."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ArtifactKind(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class ArtifactRef(StrictModel):
    uri: NonEmptyStr
    media_type: NonEmptyStr
    bytes: int = Field(ge=0)
    checksum: NonEmptyStr
    kind: ArtifactKind
