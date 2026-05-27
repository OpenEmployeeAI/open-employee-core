"""Workflow skeletons for OpenEmployee core.

Skeletons declare boundaries only. They intentionally do not depend on
``temporalio`` so this scaffold stays dependency-light; concrete workflows
will adapt these signatures to ``@workflow.defn`` once the Temporal layer
lands.
"""

from .feedback_roadmap import (
    ACTIVITY_NAME_RE,
    FeedbackToRoadmapWorkflowInput,
    FeedbackToRoadmapWorkflowResult,
    mcp_activity_name,
)

__all__ = [
    "ACTIVITY_NAME_RE",
    "FeedbackToRoadmapWorkflowInput",
    "FeedbackToRoadmapWorkflowResult",
    "mcp_activity_name",
]
