import asyncio
import unittest
from unittest import mock

from orchestrator import batch

CONFIG = {k: {"url": f"http://127.0.0.1:99{i:02d}/"} for i, k in enumerate(["hmda", "ecoa", "hpml", "ybs", "auditor"])}


def run_with(concurrency):
    state = {"now": 0, "peak": 0, "order": []}

    async def fake_send(url, payload, httpx_client=None):
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        state["order"].append(url)
        await asyncio.sleep(0.02)
        state["now"] -= 1
        return {"parsed": {"ok": True}, "raw_text": ""}

    with mock.patch.object(batch, "send", fake_send):
        results = asyncio.run(batch.run_batch({"loan": 1}, CONFIG, agents=["hmda", "ecoa", "hpml", "ybs"], verbose=False, concurrency=concurrency))
    return state, results


class ConcurrencyTests(unittest.TestCase):
    def test_default_is_one_call_at_a_time_then_the_auditor(self):
        state, results = run_with(1)
        self.assertEqual(state["peak"], 1)
        self.assertEqual(state["order"][-1], CONFIG["auditor"]["url"])      # the auditor always runs last
        self.assertEqual(list(results), ["hmda", "ecoa", "hpml", "ybs", "auditor"])
        self.assertTrue(all("elapsed_seconds" in r for r in results.values()))

    def test_higher_concurrency_overlaps_calls(self):
        state, _ = run_with(4)
        self.assertGreater(state["peak"], 1)


if __name__ == "__main__":
    unittest.main()
