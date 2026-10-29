#!/usr/bin/env python3
"""vaultctl: lint and scaffold agent-maintained vaults (LLM-wiki pattern).

Standard library only, Python 3.11+.

  vaultctl.py check <workspace>          lint every vault listed in vaults.toml + cross-vault leaks
  vaultctl.py lint <vault>               lint one vault
  vaultctl.py new <dir> --name NAME      scaffold a vault from template/vault
  vaultctl.py log <vault> <op> <title>   append an entry to log.md

Exit code 1 when errors are found (or warnings, with --strict).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

OPS = ("ingest", "query", "lint", "decision")
PERMISSIONS = (
    "personal_private",
    "company_private",
    "customer_private",
    "customer_visible",
    "deidentified_reusable",
    "public",
)
CANON_FIELDS = ("status", "canonical", "last_verified", "review_cadence")
REQUIRED = ("AGENTS.md", "index.md", "log.md", "raw", "wiki")
LOG_HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (%s) \| \S.*$" % "|".join(OPS))
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "API key (sk-)": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "Telegram bot token": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
}
WIKILINK = re.compile(r"!?\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
MDLINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TEXT_SUFFIXES = {".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".csv"}
TEMPLATE = Path(__file__).resolve().parent.parent / "template" / "vault"


@dataclass(frozen=True)
class Finding:
    level: str  # error | warn | info
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level:5} {self.path}: {self.message}"


# ---------------------------------------------------------------- helpers


def frontmatter(text: str) -> dict[str, str] | None:
    """Top-level `key: value` pairs of a YAML frontmatter block (lists ignored)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("\"'")
    return fields


def strip_code(text: str) -> str:
    """Drop fenced code blocks and inline code so example links are not checked."""
    text = re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.S | re.M)
    return re.sub(r"`[^`\n]*`", "", text)


def md_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts and ".obsidian" not in p.parts)


def text_files(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix in TEXT_SUFFIXES and ".git" not in p.parts
    )


def parse_cadence(value: str) -> int | None:
    m = re.fullmatch(r"(\d+)d", value)
    return int(m.group(1)) if m else None


def parse_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def link_targets(text: str) -> tuple[list[str], list[str]]:
    clean = strip_code(text)
    wiki = [t.strip() for t in WIKILINK.findall(clean) if t.strip()]
    md = [t for t in MDLINK.findall(clean) if not re.match(r"^([a-z][a-z0-9+.-]*:|#)", t)]
    return wiki, md


# ---------------------------------------------------------------- lint


def lint_vault(vault: Path, today: dt.date, since: str | None = None) -> list[Finding]:
    out: list[Finding] = []

    def add(level: str, path: Path | str, msg: str) -> None:
        rel = path.relative_to(vault).as_posix() if isinstance(path, Path) else path
        out.append(Finding(level, rel, msg))

    for name in REQUIRED:
        if not (vault / name).exists():
            add("error", name, "missing (every vault needs AGENTS.md, index.md, log.md, raw/, wiki/)")
    if not (vault / "wiki").is_dir():
        return out

    files = md_files(vault)
    stems: dict[str, list[Path]] = {}
    for f in files:
        stems.setdefault(f.stem.lower(), []).append(f)

    # log.md: append-only journal with one heading per operation
    log = vault / "log.md"
    if log.exists():
        previous: dt.date | None = None
        for n, line in enumerate(log.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("## "):
                continue
            m = LOG_HEADING.match(line)
            if not m:
                add("error", f"log.md:{n}", f"bad heading, expected '## [YYYY-MM-DD] <{'|'.join(OPS)}> | <title>'")
                continue
            day = parse_date(m.group(1))
            if day is None:
                add("error", f"log.md:{n}", f"invalid date {m.group(1)}")
            elif previous and day < previous:
                add("warn", f"log.md:{n}", "entry older than the one above (log.md is append-only)")
            previous = day or previous

    # wiki pages: frontmatter rules
    for f in files:
        rel = f.relative_to(vault)
        if rel.parts[0] != "wiki":
            continue
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text) or {}
        in_archive = "_archive" in rel.parts
        if len(rel.parts) > 2 and rel.parts[1] == "canon":
            if not f.name.startswith("CANON-"):
                add("warn", f, "files in wiki/canon/ should be named CANON-<topic>.md")
            missing = [k for k in CANON_FIELDS if not fm.get(k)]
            if missing:
                add("error", f, f"canon frontmatter missing: {', '.join(missing)}")
            else:
                verified = parse_date(fm["last_verified"])
                cadence = parse_cadence(fm["review_cadence"])
                if verified is None:
                    add("error", f, "last_verified must be YYYY-MM-DD")
                if cadence is None:
                    add("error", f, "review_cadence must look like '90d'")
                if verified and cadence is not None and verified + dt.timedelta(days=cadence) < today:
                    add("warn", f, f"canon overdue for review (last verified {verified}, every {cadence}d)")
        perm = fm.get("knowledge_permission")
        if perm and perm not in PERMISSIONS:
            add("error", f, f"unknown knowledge_permission '{perm}' (allowed: {', '.join(PERMISSIONS)})")
        if fm.get("status") == "superseded" and not in_archive:
            add("warn", f, "superseded page should move to wiki/_archive/")

    # links (raw/ is immutable source material: not checked)
    linked: set[Path] = set()
    for f in files:
        rel = f.relative_to(vault)
        text = f.read_text(encoding="utf-8")
        wiki, md = link_targets(text)
        for target in wiki:
            hit = resolve_wikilink(vault, stems, target)
            if hit:
                linked.add(hit)
            elif rel.parts[0] != "raw":
                add("error", f, f"broken link [[{target}]]")
        for target in md:
            path = (f.parent / target.split("#")[0]).resolve()
            if path.exists():
                linked.add(path)
            elif rel.parts[0] != "raw":
                add("error", f, f"broken link ({target})")

    # orphans: wiki pages not catalogued in index.md
    index = vault / "index.md"
    if index.exists():
        wiki_idx, md_idx = link_targets(index.read_text(encoding="utf-8"))
        indexed = {resolve_wikilink(vault, stems, t) for t in wiki_idx}
        indexed |= {(vault / t.split("#")[0]).resolve() for t in md_idx}
        for f in files:
            rel = f.relative_to(vault)
            if rel.parts[0] == "wiki" and "_archive" not in rel.parts and f.resolve() not in indexed:
                add("warn", f, "not listed in index.md")

    # secrets: never in a vault, raw included
    for f in text_files(vault):
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for name, rx in SECRET_PATTERNS.items():
                if rx.search(line):
                    add("error", f"{f.relative_to(vault).as_posix()}:{n}", f"looks like a secret ({name})")

    if since:
        out += git_checks(vault, since)
    return out


def resolve_wikilink(vault: Path, stems: dict[str, list[Path]], target: str) -> Path | None:
    """Obsidian-style: path from the vault root, or a file name / path suffix anywhere in the vault."""
    for candidate in (vault / target, vault / f"{target}.md"):
        if candidate.is_file():
            return candidate.resolve()
    name = target.removesuffix(".md").lower()
    suffix = "/" + name + ".md"
    for f in stems.get(name.rsplit("/", 1)[-1], []):
        if "/" not in name or ("/" + f.relative_to(vault).as_posix().lower()).endswith(suffix):
            return f.resolve()
    return None


def git_checks(vault: Path, since: str) -> list[Finding]:
    """raw/ is append-only; canon changes are reported for human review."""
    proc = subprocess.run(
        ["git", "-C", str(vault), "diff", "--name-status", "-M", "--relative", since, "--", "."],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return [Finding("error", ".", f"git diff {since} failed: {proc.stderr.strip()}")]
    out: list[Finding] = []
    for line in proc.stdout.splitlines():
        status, *paths = line.split("\t")
        path = paths[0]
        if path.startswith("raw/") and status != "A" and status != "R100":
            verb = {"M": "modified", "D": "deleted"}.get(status[0], f"changed ({status})")
            out.append(Finding("error", path, f"raw/ is append-only: file {verb} since {since}"))
        if any(p.startswith("wiki/canon/") or p in ("AGENTS.md", "CLAUDE.md") for p in paths):
            out.append(Finding("info", paths[-1], "canon changed: needs human approval"))
    return out


def check_workspace(workspace: Path, today: dt.date, since: str | None = None) -> list[Finding]:
    registry = workspace / "vaults.toml"
    if not registry.exists():
        return [Finding("error", "vaults.toml", "missing vault registry")]
    vaults = tomllib.loads(registry.read_text(encoding="utf-8"))
    out: list[Finding] = []
    for key, cfg in vaults.items():
        root = workspace / cfg.get("path", key)
        if not root.is_dir():
            out.append(Finding("error", f"vaults.toml [{key}]", f"path not found: {cfg.get('path', key)}"))
            continue
        prefix = root.relative_to(workspace).as_posix()
        for f in lint_vault(root, today, since):
            out.append(Finding(f.level, f"{prefix}/{f.path}", f.message))

    # scope leaks: a vault's private terms must not appear in another vault
    for key, cfg in vaults.items():
        root = workspace / cfg.get("path", key)
        allowed = set(cfg.get("may_mention", []))
        if "*" in allowed or not root.is_dir():
            continue
        foreign = [
            (other, term)
            for other, ocfg in vaults.items()
            if other != key and other not in allowed
            for term in ocfg.get("private_terms", [])
        ]
        if not foreign:
            continue
        for f in text_files(root):
            text = f.read_text(encoding="utf-8", errors="replace")
            for other, term in foreign:
                if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I):
                    rel = f.relative_to(workspace).as_posix()
                    out.append(Finding("error", rel, f"scope leak: private term of vault '{other}'"))
    return out


# ---------------------------------------------------------------- write commands


def new_vault(dest: Path, name: str, description: str) -> str:
    """Copy template/vault to dest and fill placeholders; returns the vaults.toml entry to add."""
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty directory: {dest}")
    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True)
    for f in text_files(dest):
        text = f.read_text(encoding="utf-8")
        f.write_text(text.replace("{{NAME}}", name).replace("{{DESCRIPTION}}", description), encoding="utf-8")
    slug = dest.name
    return f'[{slug}]\npath = "{dest.as_posix()}"\nrepo = "<org>/vault-{slug}"\ndescription = "{description}"'


def append_log(vault: Path, op: str, title: str, body: str, day: dt.date) -> None:
    if op not in OPS:
        raise SystemExit(f"op must be one of: {', '.join(OPS)}")
    log = vault / "log.md"
    if not log.exists():
        raise SystemExit(f"no log.md in {vault}")
    current = log.read_text(encoding="utf-8").rstrip("\n")
    entry = f"## [{day.isoformat()}] {op} | {title.strip()}"
    if body.strip():
        entry += f"\n\n{body.strip()}"
    log.write_text(f"{current}\n\n{entry}\n", encoding="utf-8")


# ---------------------------------------------------------------- CLI


def report(findings: list[Finding], strict: bool) -> int:
    for f in findings:
        print(f)
    errors = sum(f.level == "error" for f in findings)
    warns = sum(f.level == "warn" for f in findings)
    print(f"\n{errors} error(s), {warns} warning(s)")
    return 1 if errors or (strict and warns) else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vaultctl", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def lint_opts(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today(), help="YYYY-MM-DD")
        sp.add_argument("--since", help="git ref: report raw/ rewrites and canon changes since this ref")
        sp.add_argument("--strict", action="store_true", help="warnings also fail")

    sp = sub.add_parser("check", help="lint every vault of a workspace (vaults.toml) + scope leaks")
    sp.add_argument("workspace", type=Path)
    lint_opts(sp)
    sp = sub.add_parser("lint", help="lint one vault")
    sp.add_argument("vault", type=Path)
    lint_opts(sp)
    sp = sub.add_parser("new", help="scaffold a vault from template/vault")
    sp.add_argument("dest", type=Path)
    sp.add_argument("--name", required=True)
    sp.add_argument("--description", default="")
    sp = sub.add_parser("log", help="append an entry to log.md")
    sp.add_argument("vault", type=Path)
    sp.add_argument("op", choices=OPS)
    sp.add_argument("title")
    sp.add_argument("--body", default="")
    sp.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())

    a = p.parse_args(argv)
    if a.cmd == "check":
        return report(check_workspace(a.workspace, a.today, a.since), a.strict)
    if a.cmd == "lint":
        return report(lint_vault(a.vault, a.today, a.since), a.strict)
    if a.cmd == "new":
        entry = new_vault(a.dest, a.name, a.description)
        print(f"vault created: {a.dest}\nadd it to vaults.toml (by pull request):\n\n{entry}")
    elif a.cmd == "log":
        append_log(a.vault, a.op, a.title, a.body, a.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
