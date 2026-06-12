"""Structured output contracts for every agent.

Each agent forces the LLM into one of these Pydantic schemas via
`with_structured_output`, so downstream code never parses free text.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ChangeCategory(str, Enum):
    FEATURES = "Features"
    BUG_FIXES = "Bug Fixes"
    PERFORMANCE = "Performance Improvements"
    SECURITY = "Security Updates"
    REFACTORING = "Refactoring"
    INFRASTRUCTURE = "Infrastructure"
    DOCUMENTATION = "Documentation"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalyzedChange(BaseModel):
    """One logical change, possibly grouping several commits/MRs/issues."""

    category: ChangeCategory
    summary: str = Field(description="One or two sentence summary of the change")
    business_impact: str = Field(description="What this means for users or the business")
    technical_impact: str = Field(description="What this means for the system/engineers")
    risk_level: RiskLevel
    source_refs: list[str] = Field(
        default_factory=list,
        description=(
            "References to source data backing this change, e.g. 'commit:abc1234', "
            "'mr:!42', 'issue:#10'. Every change MUST be traceable to at least one ref."
        ),
    )


class ChangeAnalysis(BaseModel):
    """Output of the Repository Analyst agent."""

    changes: list[AnalyzedChange]
    themes: list[str] = Field(
        default_factory=list, description="Cross-cutting themes detected in this release"
    )
    overall_risk: RiskLevel = RiskLevel.LOW


class ReleaseNotesDraft(BaseModel):
    """Output of the Release Writer agent: all four delivery formats."""

    executive: str = Field(description="Executive version for managers (markdown)")
    technical: str = Field(description="Technical version for engineers (markdown)")
    markdown: str = Field(description="Full publish-ready markdown release notes")
    slack: str = Field(
        description="Slack-optimized version using Slack mrkdwn (*bold*, bullets, emoji)"
    )


class QAVerdict(BaseModel):
    """Output of the QA agent."""

    approved: bool
    traceability_score: float = Field(
        ge=0.0, le=1.0, description="Fraction of statements traceable to source data"
    )
    issues_found: list[str] = Field(
        default_factory=list,
        description="Hallucinations, unsupported claims or formatting problems found",
    )
    feedback: str = Field(
        default="", description="Actionable instructions for the writer if not approved"
    )
