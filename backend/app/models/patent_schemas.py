"""Bounded, manual patent worksheet input. No client-asserted verification."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(max_length=6000)]
LongText = Annotated[str, StringConstraints(max_length=12000)]


class PatentDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: LongText = ""
    problem: LongText = ""
    solution: LongText = ""
    alternatives: LongText = ""
    disclosures: LongText = ""
    contributions: LongText = ""
    officeAction: LongText = ""


class PatentMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    element: ShortText = ""
    disclosureSupport: ShortText = ""
    reference: Annotated[str, StringConstraints(max_length=1000)] = ""
    referencePassage: ShortText = ""
    status: Literal["unreviewed", "candidate", "gap", "unclear"] = "unreviewed"
    notes: ShortText = ""


class PatentWorksheet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fictional_data_only: Literal[True]
    disclosure: PatentDisclosure
    claim_mappings: list[PatentMapping] = Field(default_factory=list, max_length=50)
    reviewer_notes: LongText = ""


class PatentSnapshotResponse(BaseModel):
    id: str
    matter_id: str
    created_by: str
    worksheet: PatentWorksheet
