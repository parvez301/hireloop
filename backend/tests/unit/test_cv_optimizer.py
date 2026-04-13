import json

import pytest

from hireloop.core.cv_optimizer.optimizer import CvOptimizer
from tests.fixtures.fake_anthropic import fake_anthropic

_RESPONSE = json.dumps(
    {
        "tailored_md": "# Jane Doe\n\n## Summary\n\nSenior engineer with payments experience.",
        "changes_summary": "- Rewrote summary to target payments\n- Reordered experience bullets",
        "keywords_injected": ["payments", "distributed systems"],
        "sections_reordered": ["Experience"],
    }
)


@pytest.mark.asyncio
async def test_optimizer_rewrites_resume():
    optimizer = CvOptimizer()
    with fake_anthropic({"MASTER RESUME": _RESPONSE}):
        result = await optimizer.rewrite(
            master_resume_md="# Jane Doe\n\n## Summary\n\nSoftware engineer.",
            job_markdown="Payments engineer role.",
            keywords=["payments", "distributed systems"],
            additional_feedback=None,
        )
    assert result.tailored_md.startswith("# Jane Doe")
    assert "payments" in result.keywords_injected
    assert result.changes_summary.startswith("-")
