---
gist: "Read when: changing result structure, parse-failure handling, or any logic that repairs or discards model output."
---

# Raw and parsed results are both retained

- Results retain both raw model text and parsed JSON. Parse failures remain observable evidence instead of being discarded or silently repaired.
- A failed agent call is a result too (`parse_error` set, no parsed output). Downstream stages receive that failure evidence instead of an empty string, so absence never reads as a pass.
