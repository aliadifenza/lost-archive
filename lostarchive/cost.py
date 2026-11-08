"""Cost estimator (validation test 16).

No tokenizer is available without dependencies, so prompt size is estimated
conservatively as max(characters / 4, words × 1.33). Real tokenizer counts
will differ; treat these as planning estimates, not billing figures.
"""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    return math.ceil(max(len(text) / 4, len(text.split()) * 1.33))


def estimate_run(records) -> dict:
    """Calls and estimated prompt tokens for one logged run."""
    rounds = [r for r in records if r["type"] == "agent_round"]
    retries = sum(1 for r in rounds if r["repair_retry"])
    prompt_tokens = [estimate_tokens(r["prompt"]) for r in rounds]
    return {
        "calls": len(rounds),                 # one call per agent per round
        "repair_retry_calls": retries,        # extra calls, reported separately
        "max_prompt_tokens_est": max(prompt_tokens, default=0),
        "total_prompt_tokens_est": sum(prompt_tokens),
    }
