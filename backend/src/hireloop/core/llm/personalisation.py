"""Anti-generic forcing block for HireLoop generator prompts (Layer 5).

Source of truth: ~/Downloads/PERSONALISATION_STRATEGY.md, Layer 5 + Layer 6.
The doc's instruction is unambiguous:

    Add this block to EVERY Claude prompt in HireLoop.

The block bans hedging language ("consider highlighting", "results-driven")
and forces specificity (quote CV phrases, name the company by name, reference
numbers). Layer-6 validation (Phase 6) will use the same `BANNED_PHRASES` list
to catch outputs that slipped past the block.

Phase 5a wires this into the four existing generator system prompts as-is.
Phase 5b will refactor those generators to take structured CV / JD / cross-ref
inputs (Phases 2–4) so the rules below can be enforced against real evidence.
"""

from __future__ import annotations

# Verbatim from PERSONALISATION_STRATEGY.md lines 363-376. Single source of
# truth: importers (validator in Phase 6, prompts here) reference this list so
# any addition propagates automatically.
BANNED_PHRASES: tuple[str, ...] = (
    "consider highlighting",
    "you may want to",
    "your experience aligns",
    "strong background",
    "leverage your skills",
    "results-driven",
    "team player",
    "passionate about",
    "proven track record",
    "detail-oriented",
    "go-getter",
    "dynamic professional",
)


def _format_banned_list() -> str:
    return "\n".join(f"   - \"{phrase}\"" for phrase in BANNED_PHRASES)


# Verbatim adaptation of PERSONALISATION_STRATEGY.md lines 318-353. Wording
# preserved so the doc remains a faithful spec for what runs in production.
PERSONALISATION_BLOCK: str = f"""PERSONALISATION RULES — FOLLOW STRICTLY:

1. ALWAYS quote specific phrases, job titles, companies, and
   technologies directly from the candidate's CV and the JD.
   Never paraphrase when a direct reference is available.

2. NEVER use these phrases — they are banned:
{_format_banned_list()}
   - Any phrase that could apply to any candidate

3. ALWAYS reference specific numbers from the CV:
   - Years in a role
   - Team sizes managed
   - Quantified achievements
   If no number exists, note the absence specifically.

4. ALWAYS reference the specific company name, not "the company".
   ALWAYS reference the specific job title, not "the role".

5. If you identify a gap, name the exact skill or requirement
   from the JD and suggest a specific bridge from their CV.
   Never say "you lack experience in X" without suggesting
   what in their CV partially addresses it.

6. The output must be unrecognisable if the candidate's name
   and the company name are removed. If it still makes sense
   generically, rewrite it."""


def with_personalisation(system_prompt: str) -> str:
    """Append the anti-generic forcing block to a system prompt.

    Idempotent: re-applying is a no-op so call sites don't need to track state.
    """
    if PERSONALISATION_BLOCK in system_prompt:
        return system_prompt
    separator = "\n\n" if system_prompt and not system_prompt.endswith("\n\n") else ""
    return f"{system_prompt}{separator}{PERSONALISATION_BLOCK}"
