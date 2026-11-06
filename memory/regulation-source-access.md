---
gist: "Read when: fetching or rebuilding from eCFR, FFIEC, FEMA or FCA sources, or a source returns 403/404/406."
---

# Regulation source access

- 2026-10-08 — eCFR's versioner API needs `Accept-Encoding` compression and a date no later than the title's `up_to_date_as_of` (from `/api/versioner/v1/titles.json`), otherwise it returns 406/404. FFIEC (APOR tables), FEMA and some FCA pages return 403/404 to scripts; the source registry marks those `manual`.
