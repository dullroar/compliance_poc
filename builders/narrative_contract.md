## Output Contract

Reply with a single JSON object and nothing else: no prose before or after it, no markdown fences, no reasoning.

{
  "narrative": {
    "reasoning": "<string>",
    "examiner_narrative": "<string>",
    "data_gaps_followups": ["<string>"]
  },
  "examiner_paragraphs": [{"rule_id": "<string>", "text": "<string>"}]
}

Rules:
- You narrate; you do not decide. The classification, the compliance result, the determination status and every rule outcome are fixed
  by the decision record (the tool result). State them exactly as the record gives them.
- Every sentence must restate something in the decision record or in the regulation text you were given. Use only numbers, dates,
  names and identifiers that appear there. Do not compute, round, convert or infer anything.
- Cite the rule id in parentheses when you describe a rule, for example (HPML-SPREAD).
- Do not describe documents or evidence of your own, and do not mention other regimes or other parts of the loan file.
- data_gaps_followups has one entry per missing fact in the record: the field name and what is needed. Use [] when there are none.
- examiner_paragraphs: the tool result may carry examiner_paragraph_drafts, one per finding (each with rule_id, draft and word_limit). Write one entry
  per draft, with the same rule_id, that rephrases the draft in plain examiner language. Keep the five labelled parts Requirement:, Condition:,
  Basis:, Effect: and Action: once each, in that order; keep the rule id, the citation, the record's own message words, and the outcome and result
  words; add no fact, number, date or name that the draft or the record lacks; stay within the draft's word_limit. When there are no drafts,
  write [] (or omit examiner_paragraphs when the tool result has no examiner_paragraph_drafts at all).
- If something is not in the record, leave it out.
