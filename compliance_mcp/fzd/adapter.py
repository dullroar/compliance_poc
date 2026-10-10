"""Maps a loan payload to the FZD tool call and a decision record to report extras."""
from compliance_common.adapter import make_adapter

from .rules import EVALUATOR_VERSION

_adapter = make_adapter("fzd", EVALUATOR_VERSION)
TOOL, tool_arguments, unavailable, extras = _adapter.TOOL, _adapter.tool_arguments, _adapter.unavailable, _adapter.extras
