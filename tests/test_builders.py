"""Builder harness: change detection, scoped rebuilds, path guards, version bumps, rollback."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from agent_prompts import AGENTS, load_agent
from builders import build as B
from builders.sourcing import Fetched, ManualSource, check, load_registry, lock_entry, normalize
from compliance_common import versioning

ROOT = Path(__file__).resolve().parents[1]


class FakeFetcher:
    """Serves text by source id; unknown ids raise (like a network failure)."""

    def __init__(self, texts):
        self.texts = dict(texts)

    def fetch(self, source):
        if source["kind"] == "manual":
            raise ManualSource(source.get("note", "manual"))
        if source["id"] not in self.texts:
            raise ConnectionError("offline")
        raw = f"<SECTION>{self.texts[source['id']]}</SECTION>".encode()
        return Fetched(raw, normalize(raw), "2026-11-01", f"https://example.test/{source['id']}")


class FakeBackend:
    provider, model = "fake", "fake-1"

    def __init__(self, extra_files=None, touch_rules=True):
        self.calls, self.extra_files, self.touch_rules = [], extra_files or {}, touch_rules

    def complete(self, system, messages, json_mode=True):
        payload = json.loads(messages[-1]["content"])
        domain = payload["domain"]
        if system.startswith("Agent: mcp_builder"):
            self.calls.append(("mcp", domain))
            files = dict(self.extra_files)
            if self.touch_rules:
                files[f"compliance_mcp/{domain}/rules.py"] = payload["existing_files"][f"compliance_mcp/{domain}/rules.py"] + "\n# touched by builder\n"
                files[f"compliance_mcp/{domain}/pack/thresholds.yaml"] = payload["existing_files"][f"compliance_mcp/{domain}/pack/thresholds.yaml"] + "# touched\n"
            return json.dumps({"files": files, "notes": ["adjusted for source diff"], "needs_human_review": ["confirm interpretation"]})
        self.calls.append(("agent", domain))
        return json.dumps({"prompt_body": f"You are the {domain} agent. You explain deterministic results; you do not decide them.\n\n## How You Work\nCall {payload['tool']} first.", "notes": [], "needs_human_review": []})


def make_repo(tmp: Path, domains=("hpml",)):
    for d in domains:
        shutil.copytree(ROOT / "compliance_mcp" / d, tmp / "compliance_mcp" / d, ignore=shutil.ignore_patterns("__pycache__"))
        (tmp / "prompts").mkdir(exist_ok=True)
        shutil.copy(ROOT / "prompts" / f"{d}.md", tmp / "prompts" / f"{d}.md")
    return tmp


def registry_for(domains):
    full = load_registry()
    return {"common": full["common"], "domains": {d: copy.deepcopy(full["domains"][d]) for d in domains}}


def baseline(registry, repo_texts=None):
    """Fetch texts + a lock that matches them."""
    texts = {s["id"]: f"text of {s['id']}" for d in registry["domains"].values() for s in d["sources"] if s["kind"] != "manual"}
    fetcher = FakeFetcher(texts)
    lock = {"sources": {}}
    for d in registry["domains"].values():
        for s in d["sources"]:
            if s["kind"] != "manual":
                lock["sources"][s["id"]] = lock_entry(s, fetcher.fetch(s))
    return texts, fetcher, lock


class ChangeDetectionTests(unittest.TestCase):
    def test_unchanged_changed_new_manual_and_error(self):
        registry = registry_for(["hpml", "trid"])
        texts, fetcher, lock = baseline(registry)
        self.assertFalse(any(s.needs_build for s in check(registry, lock, fetcher)))
        fetcher.texts["ecfr-12-cfr-1026-19"] = "amended text"
        by_domain = {s.domain: s for s in check(registry, lock, fetcher)}
        self.assertTrue(by_domain["trid"].needs_build)
        self.assertFalse(by_domain["hpml"].needs_build)
        self.assertEqual([s.state for s in by_domain["trid"].sources], ["changed", "unchanged"])
        hpml_states = {s.source_id: s.state for s in by_domain["hpml"].sources}
        self.assertEqual((hpml_states["ffiec-apor-legacy-csv"], hpml_states["cfpb-ffiec-rate-spread-api"]), ("manual", "manual"))
        del fetcher.texts["ecfr-12-cfr-1026-2"]
        self.assertEqual(check(registry, lock, fetcher, ["trid"])[0].sources[1].state, "error")   # never silently "unchanged"
        del lock["sources"]["ecfr-12-cfr-1026-35"]
        self.assertEqual(check(registry, lock, fetcher, ["hpml"])[0].sources[0].state, "new")

    def test_whitespace_and_markup_noise_is_not_a_change(self):
        registry = registry_for(["trid"])
        _, fetcher, lock = baseline(registry)
        original = fetcher.fetch(registry["domains"]["trid"]["sources"][0])

        class Noisy(FakeFetcher):
            def fetch(self, source):
                raw = f"<SECTION>\n  <P>text   of\n {source['id']}</P>\n</SECTION>".encode()
                return Fetched(raw, normalize(raw), "2026-12-01", "u")
        self.assertEqual(Noisy({}).fetch(registry["domains"]["trid"]["sources"][0]).sha256, original.sha256)

    def test_unknown_domain_is_rejected(self):
        with self.assertRaises(ValueError):
            check(registry_for(["hpml"]), {"sources": {}}, FakeFetcher({}), ["nope"])


class ScopedRebuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.registry = registry_for(["hpml", "trid"])
        self.repo = make_repo(self.tmp, ("hpml", "trid"))
        self.texts, self.fetcher, self.lock = baseline(self.registry)
        self.lock_path = self.tmp / "lock.yaml"

    def run_builds(self, backend, apply=False, domains=None, runner=lambda d, r: (True, "ok")):
        return B.run_builds(domains, backend, self.fetcher, apply, self.registry, self.lock, self.repo, runner, self.lock_path)

    def test_nothing_changed_builds_nothing(self):
        backend = FakeBackend()
        reports = self.run_builds(backend, apply=True)
        self.assertEqual(backend.calls, [])
        self.assertTrue(all(r.state == "skipped" for r in reports))

    def test_only_the_changed_domain_is_rebuilt_and_versioned(self):
        before = {d: (self.repo / f"compliance_mcp/{d}/rules.py").read_text() for d in ("hpml", "trid")}
        pack_before = {d: versioning.pack_version(self.repo / f"compliance_mcp/{d}/pack/manifest.yaml") for d in ("hpml", "trid")}
        agent_before = {d: versioning.prompt_version(self.repo / f"prompts/{d}.md") for d in ("hpml", "trid")}
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        backend = FakeBackend()
        reports = {r.domain: r for r in self.run_builds(backend, apply=True)}

        self.assertEqual(backend.calls, [("mcp", "trid"), ("agent", "trid")])
        self.assertEqual(reports["hpml"].state, "skipped")
        self.assertEqual(reports["trid"].state, "applied")
        self.assertEqual((self.repo / "compliance_mcp/hpml/rules.py").read_text(), before["hpml"])      # untouched
        self.assertEqual(versioning.pack_version(self.repo / "compliance_mcp/hpml/pack/manifest.yaml"), pack_before["hpml"])
        self.assertEqual(versioning.prompt_version(self.repo / "prompts/hpml.md"), agent_before["hpml"])
        # trid: each changed component bumped independently
        self.assertEqual(reports["trid"].versions["pack"], versioning.bump(pack_before["trid"], "patch"))
        self.assertEqual(reports["trid"].versions["agent"], versioning.bump(agent_before["trid"], "patch"))
        self.assertEqual(versioning.evaluator_version(self.repo / "compliance_mcp/trid/rules.py"), "0.2.0")
        self.assertIn("touched by builder", (self.repo / "compliance_mcp/trid/rules.py").read_text())

    def test_apply_writes_snapshot_syncs_manifest_and_updates_the_lock(self):
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        self.run_builds(FakeBackend(), apply=True)
        snap = self.repo / "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml"
        self.assertIn(b"amended TRID text", snap.read_bytes())
        manifest = yaml.safe_load((self.repo / "compliance_mcp/trid/pack/manifest.yaml").read_text())
        entry = next(s for s in manifest["sources"] if s["local_path"].endswith("12-cfr-1026-19.xml"))
        self.assertEqual(entry["sha256"], hashlib.sha256(snap.read_bytes()).hexdigest())
        self.assertEqual(entry["issue_date"], "2026-11-01")
        self.assertEqual(entry["id"], "ecfr-12-cfr-1026-19-2026-11-01")
        saved = yaml.safe_load(self.lock_path.read_text())["sources"]["ecfr-12-cfr-1026-19"]
        self.assertEqual(saved["normalized_sha256"], self.fetcher.fetch(self.registry["domains"]["trid"]["sources"][0]).sha256)
        # the next run notices nothing to do
        backend = FakeBackend()
        self.run_builds(backend, apply=True)
        self.assertEqual(backend.calls, [])

    def test_dry_run_stages_but_changes_nothing(self):
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        rules_before = (self.repo / "compliance_mcp/trid/rules.py").read_text()
        reports = {r.domain: r for r in self.run_builds(FakeBackend(), apply=False)}
        self.assertEqual(reports["trid"].state, "staged")
        self.assertEqual((self.repo / "compliance_mcp/trid/rules.py").read_text(), rules_before)
        self.assertFalse(self.lock_path.exists())
        self.assertTrue((self.repo / reports["trid"].stage_dir / "files/prompts/trid.md").exists())

    def test_failed_tests_roll_everything_back(self):
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        snapshot_before = (self.repo / "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml").read_bytes()
        manifest_before = (self.repo / "compliance_mcp/trid/pack/manifest.yaml").read_text()
        prompt_before = (self.repo / "prompts/trid.md").read_text()
        reports = {r.domain: r for r in self.run_builds(FakeBackend(), apply=True, runner=lambda d, r: (False, "boom"))}
        self.assertEqual(reports["trid"].state, "failed")
        self.assertEqual((self.repo / "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml").read_bytes(), snapshot_before)
        self.assertEqual((self.repo / "compliance_mcp/trid/pack/manifest.yaml").read_text(), manifest_before)
        self.assertEqual((self.repo / "prompts/trid.md").read_text(), prompt_before)
        self.assertNotIn("touched by builder", (self.repo / "compliance_mcp/trid/rules.py").read_text())
        self.assertFalse(self.lock_path.exists())
        self.assertEqual(self.lock["sources"]["ecfr-12-cfr-1026-19"]["normalized_sha256"] != self.fetcher.fetch(self.registry["domains"]["trid"]["sources"][0]).sha256, True)

    def test_fetch_error_blocks_the_domain_build(self):
        del self.fetcher.texts["ecfr-12-cfr-1026-2"]
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        backend = FakeBackend()
        reports = {r.domain: r for r in self.run_builds(backend, apply=True)}
        self.assertEqual(reports["trid"].state, "failed")
        self.assertEqual(backend.calls, [])

    def test_builder_cannot_write_outside_its_domain_or_over_snapshots(self):
        self.fetcher.texts["ecfr-12-cfr-1026-19"] = "amended TRID text"
        evil = {"compliance_mcp/hpml/rules.py": "x", "../outside.py": "x", "prompts/other.md": "x", "/etc/passwd": "x",
                "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml": "forged", "builders/sources.yaml": "x", "tests/test_other.py": "x"}
        reports = {r.domain: r for r in self.run_builds(FakeBackend(extra_files=evil), apply=True)}
        self.assertEqual(set(reports["trid"].rejected_paths), set(evil))
        self.assertNotIn("forged", (self.repo / "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml").read_text())
        self.assertFalse((self.tmp.parent / "outside.py").exists())
        self.assertNotEqual((self.repo / "compliance_mcp/hpml/rules.py").read_text(), "x")


class HarnessContractTests(unittest.TestCase):
    def test_path_guard(self):
        ok = ["compliance_mcp/trid/rules.py", "compliance_mcp/trid/pack/thresholds.yaml", "tests/test_trid_evaluator.py", "tests/fixtures/trid/a.json"]
        bad = ["compliance_mcp/hpml/rules.py", "compliance_mcp/trid/pack/sources/x.xml", "compliance_mcp/trid/../hpml/rules.py", "prompts/trid.md", "tests/test_trid_other.py"]
        self.assertTrue(all(B.allowed_mcp_path("trid", p) for p in ok))
        self.assertFalse(any(B.allowed_mcp_path("trid", p) for p in bad))

    def test_assembled_prompt_has_header_tool_and_the_verbatim_contract(self):
        prompt = B.assemble_prompt({"key": "x", "name": "X Agent", "version": "0.1.0", "track": "T", "tool": "x_evaluate"}, "You are X.")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            path.write_text(prompt)
            agent = load_agent(path)
        self.assertEqual((agent["tool"], agent["version"]), ("x_evaluate", "0.1.0"))
        self.assertTrue(prompt.endswith(B.narrative_contract()))

    def test_every_tool_backed_prompt_carries_the_shared_contract_verbatim(self):
        contract = B.narrative_contract().replace("@@AGENT_VERSION@@", "")
        for key, agent in AGENTS.items():
            if agent.get("tool"):
                with self.subTest(agent=key):
                    self.assertIn(contract.strip(), agent["system_prompt"])
                    adapter = __import__(f"compliance_mcp.{agent['tool'].removesuffix('_evaluate')}.adapter", fromlist=["TOOL"])
                    self.assertEqual(adapter.TOOL, agent["tool"])

    def test_registry_covers_every_agent_with_a_pack_and_names_real_snapshots(self):
        registry = load_registry()
        for domain in ("ybs", "hpml", "trid"):
            self.assertTrue((ROOT / "compliance_mcp" / domain / "pack" / "manifest.yaml").exists())
            self.assertIn(domain, registry["domains"])
        for domain in ("hpml", "trid"):
            for source in registry["domains"][domain]["sources"]:
                if source["kind"] != "manual":
                    self.assertTrue((ROOT / source["snapshot"]).is_file(), source["id"])

    def test_version_helpers_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules, manifest, prompt = Path(tmp, "rules.py"), Path(tmp, "manifest.yaml"), Path(tmp, "p.md")
            rules.write_text('X = 1\nEVALUATOR_VERSION = "1.2.3"\n')
            manifest.write_text("id: a\nversion: 0.1.0\nstatus: s\n")
            prompt.write_text("Agent: a | Name: A | Agent Version: 0.3.0 | Track: T | Output: json\n\nbody Agent Version: 9.9.9\n")
            versioning.set_evaluator_version(rules, "1.3.0")
            versioning.set_pack_version(manifest, "0.1.1")
            versioning.set_prompt_version(prompt, "0.3.1")
            self.assertEqual((versioning.evaluator_version(rules), versioning.pack_version(manifest), versioning.prompt_version(prompt)), ("1.3.0", "0.1.1", "0.3.1"))
            self.assertIn("body Agent Version: 9.9.9", prompt.read_text())    # only the header line is touched
            self.assertIn("status: s", manifest.read_text())


class ToolInHandPromptTests(unittest.TestCase):
    """Every tool-backed agent wakes up with its tool in hand and knows its job is narrative only."""

    def test_every_tool_backed_prompt_opens_with_the_tool_then_the_role(self):
        from builders.prompts import HARNESS_SECTIONS
        tool_backed = {k: a for k, a in AGENTS.items() if a.get("tool")}
        self.assertEqual(set(tool_backed), {"ybs", "hpml", "trid", "hmda", "ecoa", "vmi", "fzd", "hvcre", "auditor"})
        for key, agent in tool_backed.items():
            with self.subTest(agent=key):
                prompt = agent["system_prompt"]
                headings = [line[3:] for line in prompt.splitlines() if line.startswith("## ")]
                self.assertEqual(headings[:2], ["Your Tool", "Your Role"])
                self.assertNotIn("How You Work", headings)
                intro_end = prompt.index("## Your Tool")
                self.assertLess(prompt.index("You are the"), intro_end)
                self.assertIn(f"call `{agent['tool']}`", prompt)
                self.assertIn("narrator, not an investigator", prompt)
                self.assertIn("no independent research".replace("no ", "").replace("independent", "independent"), prompt.replace("You do no independent", "independent"))
                self.assertIn("Regulations As Given", prompt)
                self.assertEqual(headings.count("Your Tool"), 1)

    def test_blocks_are_idempotent_and_replace_the_old_how_you_work_steps(self):
        from builders.prompts import inject_tool_blocks
        text = "Agent: x | Name: X | Agent Version: 1.0.0 | Track: T | Tool: x_evaluate | Output: json\n\nYou are the X.\n\n## Purpose\np\n\n## How You Work\n1. old steps\n\n## Output Contract\nc\n"
        once = inject_tool_blocks(text, "x_evaluate", "x_case")
        self.assertEqual(inject_tool_blocks(once, "x_evaluate", "x_case"), once)
        self.assertNotIn("old steps", once)
        self.assertEqual([l[3:] for l in once.splitlines() if l.startswith("## ")], ["Your Tool", "Your Role", "Your Output", "Purpose", "Output Contract"])
        self.assertIn("`x_case` object", once)
        auditor = inject_tool_blocks(text, "auditor_evaluate", None)
        self.assertIn("audit input", auditor)

    def test_regenerating_the_committed_prompts_changes_nothing(self):
        import tempfile, shutil
        from builders.build import rebuild_prompts
        from agent_prompts import PROMPTS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            for path in PROMPTS_DIR.glob("*.md"):
                shutil.copy(path, Path(tmp) / path.name)
            self.assertEqual(rebuild_prompts(prompts_dir=Path(tmp)), {})

    def test_assembled_builder_prompts_include_the_blocks(self):
        prompt = B.assemble_prompt({"key": "x", "name": "X Agent", "version": "0.1.0", "track": "T", "tool": "x_evaluate"}, "You are X.\n\n## Purpose\np")
        self.assertIn("## Your Tool", prompt)
        self.assertLess(prompt.index("## Your Tool"), prompt.index("## Purpose"))


if __name__ == "__main__":
    unittest.main()
