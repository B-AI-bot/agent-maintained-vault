import datetime as dt
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("vaultctl", ROOT / "tools" / "vaultctl.py")
vaultctl = importlib.util.module_from_spec(spec)
sys.modules["vaultctl"] = vaultctl
spec.loader.exec_module(vaultctl)

TODAY = dt.date(2026, 1, 25)


def messages(findings, level=None):
    return [f"{f.path}: {f.message}" for f in findings if level is None or f.level == level]


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.vault = self.tmp / "v"
        vaultctl.new_vault(self.vault, "Test", "A test vault.")

    def write(self, rel, text):
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def index(self, *pages):
        self.write("index.md", "# Index\n\n" + "\n".join(f"- [[{p}]]" for p in pages) + "\n")


class TestExampleWorkspace(unittest.TestCase):
    def test_example_is_clean(self):
        findings = vaultctl.check_workspace(ROOT / "example", TODAY)
        self.assertEqual(messages(findings), [])


class TestLint(VaultCase):
    def test_fresh_vault_is_clean(self):
        self.assertEqual(messages(vaultctl.lint_vault(self.vault, TODAY)), [])

    def test_missing_structure(self):
        (self.vault / "log.md").unlink()
        self.assertIn("log.md: missing", messages(vaultctl.lint_vault(self.vault, TODAY), "error")[0])

    def test_canon_frontmatter_required(self):
        self.write("wiki/canon/CANON-x.md", "---\nstatus: active\n---\n# X\n")
        self.index("CANON-x")
        errors = messages(vaultctl.lint_vault(self.vault, TODAY), "error")
        self.assertEqual(len(errors), 1)
        self.assertIn("canonical, last_verified, review_cadence", errors[0])

    def test_stale_canon_warns(self):
        self.write(
            "wiki/canon/CANON-x.md",
            "---\nstatus: active\ncanonical: true\nlast_verified: 2025-01-01\nreview_cadence: 30d\n---\n",
        )
        self.index("CANON-x")
        warns = messages(vaultctl.lint_vault(self.vault, TODAY), "warn")
        self.assertEqual(len(warns), 1)
        self.assertIn("overdue", warns[0])

    def test_broken_links_but_not_in_code(self):
        self.write("wiki/a.md", "See [[missing]] and [b](b.md).\n\n```\n[[in-code]]\n```\nand `[[inline]]`\n")
        self.index("a")
        errors = messages(vaultctl.lint_vault(self.vault, TODAY), "error")
        self.assertEqual(len(errors), 2)
        self.assertIn("[[missing]]", errors[0])
        self.assertIn("(b.md)", errors[1])

    def test_wikilink_by_name_alias_and_heading(self):
        self.write("wiki/projects/target.md", "# T\n")
        self.write("wiki/a.md", "[[target|alias]] [[projects/target#T]] [[wiki/projects/target]]\n")
        self.index("a", "target")
        self.assertEqual(messages(vaultctl.lint_vault(self.vault, TODAY)), [])

    def test_orphan_page_warns(self):
        self.write("wiki/lonely.md", "# Lonely\n")
        self.assertIn("not listed in index.md", messages(vaultctl.lint_vault(self.vault, TODAY), "warn")[0])

    def test_archive_is_not_orphan_and_superseded_must_move(self):
        self.write("wiki/_archive/old.md", "---\nstatus: superseded\n---\n")
        self.write("wiki/stale.md", "---\nstatus: superseded\n---\n")
        self.index("stale")
        warns = messages(vaultctl.lint_vault(self.vault, TODAY), "warn")
        self.assertEqual(warns, ["wiki/stale.md: superseded page should move to wiki/_archive/"])

    def test_unknown_permission(self):
        self.write("wiki/a.md", "---\nknowledge_permission: secret\n---\n")
        self.index("a")
        self.assertIn("unknown knowledge_permission", messages(vaultctl.lint_vault(self.vault, TODAY), "error")[0])

    def test_bad_log_heading(self):
        self.write("log.md", "# Log\n\n## [2026-01-02] ingest | ok\n\n## 2026-01-03 notes\n")
        errors = messages(vaultctl.lint_vault(self.vault, TODAY), "error")
        self.assertEqual(len(errors), 1)
        self.assertIn("log.md:5", errors[0])

    def test_secret_detected_in_raw(self):
        fake = "AKIA" + "ABCDEFGHIJKLMNOP"  # split so secret scanners ignore this test file
        self.write("raw/2026-01-01-export.md", f"key = {fake}\n")
        errors = messages(vaultctl.lint_vault(self.vault, TODAY), "error")
        self.assertEqual(len(errors), 1)
        self.assertIn("AWS access key", errors[0])


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.ws)
        for slug in ("company", "client-a"):
            vaultctl.new_vault(self.ws / slug, slug, "")
        (self.ws / "vaults.toml").write_text(
            '[company]\npath = "company"\n\n[client-a]\npath = "client-a"\nprivate_terms = ["Codename Blue"]\n'
        )

    def test_scope_leak(self):
        (self.ws / "company/raw/notes.md").write_text("Met them about codename blue.\n")
        (self.ws / "client-a/raw/notes.md").write_text("Codename Blue kickoff.\n")
        errors = messages(vaultctl.check_workspace(self.ws, TODAY), "error")
        self.assertEqual(errors, ["company/raw/notes.md: scope leak: private term of vault 'client-a'"])

    def test_may_mention(self):
        toml = (self.ws / "vaults.toml").read_text().replace('path = "company"', 'path = "company"\nmay_mention = ["client-a"]')
        (self.ws / "vaults.toml").write_text(toml)
        (self.ws / "company/raw/notes.md").write_text("Codename Blue.\n")
        self.assertEqual(messages(vaultctl.check_workspace(self.ws, TODAY)), [])


@unittest.skipUnless(shutil.which("git"), "git not installed")
class TestGitChecks(VaultCase):
    def git(self, *args):
        subprocess.run(["git", "-C", str(self.vault), *args], check=True, capture_output=True)

    def setUp(self):
        super().setUp()
        self.write("raw/2026-01-01-source.md", "original\n")
        self.git("init", "-q")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")

    def test_raw_append_is_fine_rewrite_is_not(self):
        self.write("raw/2026-01-02-new.md", "new\n")
        self.git("add", "-A")
        self.assertEqual(messages(vaultctl.lint_vault(self.vault, TODAY, since="HEAD"), "error"), [])
        self.write("raw/2026-01-01-source.md", "edited\n")
        errors = messages(vaultctl.lint_vault(self.vault, TODAY, since="HEAD"), "error")
        self.assertEqual(errors, ["raw/2026-01-01-source.md: raw/ is append-only: file modified since HEAD"])

    def test_canon_change_is_reported(self):
        self.write(
            "wiki/canon/CANON-x.md",
            "---\nstatus: active\ncanonical: true\nlast_verified: 2026-01-20\nreview_cadence: 30d\n---\n",
        )
        self.index("CANON-x")
        self.git("add", "-A")
        infos = messages(vaultctl.lint_vault(self.vault, TODAY, since="HEAD"), "info")
        self.assertEqual(infos, ["wiki/canon/CANON-x.md: canon changed: needs human approval"])


class TestCommands(VaultCase):
    def test_new_fills_placeholders(self):
        text = (self.vault / "AGENTS.md").read_text()
        self.assertIn("Vault: Test", text)
        self.assertNotIn("{{", text)

    def test_new_refuses_non_empty(self):
        with self.assertRaises(SystemExit):
            vaultctl.new_vault(self.vault, "Again", "")

    def test_log_appends_valid_entry(self):
        vaultctl.append_log(self.vault, "ingest", "Kickoff notes", "Created [[a]].", dt.date(2026, 1, 3))
        log = (self.vault / "log.md").read_text()
        self.assertTrue(log.endswith("## [2026-01-03] ingest | Kickoff notes\n\nCreated [[a]].\n"))

    def test_cli_exit_codes(self):
        self.assertEqual(vaultctl.main(["lint", str(self.vault), "--today", "2026-01-25"]), 0)
        self.write("wiki/lonely.md", "# Lonely\n")
        self.assertEqual(vaultctl.main(["lint", str(self.vault)]), 0)
        self.assertEqual(vaultctl.main(["lint", str(self.vault), "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
