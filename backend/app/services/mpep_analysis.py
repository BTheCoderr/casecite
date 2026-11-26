"""Evidence-bounded, fictional-data patent issue spotting."""

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.llm_clients import openai_chat
from app.services.mpep import Hit, SearchResult
from app.services.rag.prompt_safety import UNTRUSTED_CONTENT_RULE, untrusted_block

NOTICE = (
    "AI-assisted draft questions only. Exact quote matching is not a determination of "
    "legal relevance, current law, patentability, or correct interpretation. Practitioner review required."
)


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passage_id: int = Field(ge=1, le=20)
    question: str = Field(min_length=5, max_length=600)
    quote: str = Field(min_length=12, max_length=900)


class Proposals(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issues: list[Proposal] = Field(max_length=8)


class Issue(BaseModel):
    question: str
    citation: Hit


class AnalysisResult(BaseModel):
    notice: str = NOTICE
    issues: list[Issue]
    rejected: int
    source_count: int


def validate_proposals(raw: str, evidence: SearchResult) -> AnalysisResult:
    # Reject the entire malformed response; never render raw provider output.
    try:
        parsed = Proposals.model_validate_json(raw)
    except ValidationError:
        return AnalysisResult(issues=[], rejected=1, source_count=len(evidence.hits))
    issues: list[Issue] = []
    rejected = 0
    for proposal in parsed.issues:
        index = proposal.passage_id - 1
        if index >= len(evidence.hits):
            rejected += 1
            continue
        hit = evidence.hits[index]
        # The exact quote must come from the specific retrieved passage, not
        # another passage on the page or a plausible but fabricated citation.
        offset = hit.quote.find(proposal.quote)
        if offset < 0 or not proposal.question.strip().endswith("?"):
            rejected += 1
            continue
        start = hit.start + offset
        citation = hit.model_copy(
            update={"quote": proposal.quote, "start": start, "end": start + len(proposal.quote)}
        )
        issues.append(Issue(question=proposal.question, citation=citation))
    return AnalysisResult(issues=issues, rejected=rejected, source_count=len(evidence.hits))


def build_prompt(topic: str, evidence: SearchResult) -> str:
    passages = [
        {"passage_id": i, "section": hit.section, "text": hit.quote}
        for i, hit in enumerate(evidence.hits, start=1)
    ]
    return (
        "Prepare at most eight questions for a patent practitioner's review. "
        "Do not decide patentability or give filing or deadline instructions. "
        "Every question must be a question, with one exact verbatim quote of 12-900 characters "
        "from its numbered passage. Do not invent sources. Return JSON only: "
        '{"issues":[{"passage_id":1,"question":"...?", "quote":"..."}]}. '
        "Return an empty issues array if there is insufficient evidence.\n"
        + UNTRUSTED_CONTENT_RULE
        + "\n"
        + untrusted_block("Fictional research topic", topic)
        + "\n"
        + untrusted_block("Retrieved MPEP passages", json.dumps(passages, ensure_ascii=False))
    )


async def draft_questions(
    client, model: str, endpoint: str, topic: str, evidence: SearchResult
) -> AnalysisResult:
    if not evidence.hits:
        return AnalysisResult(issues=[], rejected=0, source_count=0)
    response = await openai_chat(
        client,
        purpose="patent_issue_preview",
        required_base_url=endpoint,
        model=model,
        messages=[{"role": "user", "content": build_prompt(topic, evidence)}],
        max_tokens=1500,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return validate_proposals(response.choices[0].message.content or "", evidence)
