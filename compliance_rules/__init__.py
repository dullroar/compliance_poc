"""Offline, deterministic compliance evaluators.

These evaluators deliberately contain no model or network calls.  A rule-pack
version and the input facts completely determine the substantive result.
"""

from .ybs import evaluate_ybs

__all__ = ["evaluate_ybs"]
