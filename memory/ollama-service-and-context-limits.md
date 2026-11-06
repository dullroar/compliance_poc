---
gist: "Read when: Ollama output is truncated or plausible-but-wrong, a long run is interrupted, the Ollama service settings need changing, or fit and speed of a loaded model are in question."
---

# Ollama service and context limits

- 2026-10-08 — Ollama silently truncates input beyond its context window. The builder agents send ~25-100 KB prompts; set `OLLAMA_NUM_CTX` (honored in `agents/backends.py`) or use a remote model, otherwise a truncated prompt produces plausible-looking but wrong builder output.
- 2026-10-09 — If the machine sleeps mid-run, WSL's clock jumps but process timeouts use monotonic time, so an in-flight Ollama call just resumes and finishes after wake (observed: 2 h wall gap, HPML call completed). Keep the machine awake for long runs anyway.
- 2026-10-09 — CORRECTION: Ollama runs as a systemd service inside WSL (`/etc/systemd/system/ollama.service`, drop-in `ollama.service.d/override.conf` sets OLLAMA_NO_CLOUD=1 and OLLAMA_CONTEXT_LENGTH=65536 — that 65k default is why unconfigured models load with a big context). Changing the service needs sudo, which needs a password the agent does not have; ask the user to apply it. Restarting it kills any benchmark or batch in flight.
- 2026-10-09 — pancode-coder (qwen2.5-coder:7b-instruct-q4_K_M, num_ctx 32768, num_predict 4096) baseline under the CURRENT Ollama settings (f16 KV cache): 6.8 GB loaded, 12%/88% CPU/GPU split, 43.8 tok/s generation, 623 tok/s prompt eval, 8.7 s load. The planned OLLAMA_FLASH_ATTENTION=1 / OLLAMA_KV_CACHE_TYPE=q8_0 / NUM_PARALLEL=1 / MAX_LOADED_MODELS=1 override needs sudo to apply and affects every model; re-measure fit after applying it.
