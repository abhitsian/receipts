"""Receipts — Claude Code session parser.

Lifted from claude-desk's session_parser.py and fixed in two ways:

  1. Token math. claude-desk summed only input_tokens + output_tokens. With
     prompt caching on, input_tokens is tiny (often 1-3) because the real
     volume sits in cache_creation_input_tokens / cache_read_input_tokens.
     Counting only input+output undercounts real usage by ~100x. We count
     all four.
  2. Dedup. The same request can appear on multiple lines; we count each
     requestId once.

Reads ~/.claude/projects/**/*.jsonl. Pure stdlib, no dependencies.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# File extensions used to tell "code work" from "the stuff non-coders do".
CODE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java",
    ".rb", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt",
    ".scala", ".sh", ".bash", ".zsh", ".sql", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte", ".lua", ".r", ".dart", ".ex", ".exs", ".pl", ".clj",
    ".hs", ".elm", ".tf",
}
DOC_EXTS = {".md", ".markdown", ".txt", ".rst", ".doc", ".docx", ".pdf", ".rtf"}
DATA_EXTS = {".csv", ".tsv", ".xlsx", ".xls", ".yaml", ".yml", ".parquet"}

# Rough "manual minutes" each tool action stands in for. Deliberately
# conservative — this drives the "time saved" estimate, and over-claiming
# there poisons the whole tool's credibility. Tunable in one place.
TOOL_MINUTES = {
    "Write": 6.0, "Edit": 2.0, "MultiEdit": 4.0, "NotebookEdit": 4.0,
    "Bash": 1.5, "WebFetch": 3.0, "WebSearch": 3.0, "Agent": 8.0, "Task": 8.0,
    "Read": 0.3, "Grep": 0.3, "Glob": 0.3, "LS": 0.2,
}
SESSION_MINUTES_CAP = 240  # no single session claims more than 4 hours


@dataclass
class Receipt:
    """One Claude Code session, parsed into something shareable."""

    session_id: str
    project: str
    title: str
    prompt: str          # cleaned first user message — the copyable bit
    start: datetime      # local time
    end: datetime        # local time
    duration_min: int
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    tool_count: int
    files_created: list = field(default_factory=list)
    category: str = "non-code"   # code | non-code | mixed
    task_type: str = "Thinking & planning"
    minutes_saved: int = 0
    hourly: dict = field(default_factory=dict)  # "YYYY-MM-DD HH" (local) -> tokens
    is_active: bool = False

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


def _parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _extract_text(content) -> str:
    """Pull plain text out of a message's content (str or block list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def _clean_prompt(text: str) -> str:
    """Turn a raw first-user-message into something fit for a brag card."""
    if not text:
        return ""
    text = text.strip()

    # Slash command? Show it as the command + its args.
    cmd = re.search(r"<command-name>\s*/?(\S+?)\s*</command-name>", text)
    if cmd:
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        a = (args.group(1).strip() if args else "")
        return (f"/{cmd.group(1)} {a}").strip()

    # Strip harness-injected blocks and any stray XML-ish tags.
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<command-[^>]*>.*?</command-[^>]*>", "", text, flags=re.S)
    text = re.sub(r"<local-command[^>]*>.*?</local-command[^>]*>", "", text, flags=re.S)
    text = re.sub(r"Caveat:.*?(?:\n|$)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()

    if len(text) > 360:
        text = text[:357].rstrip() + "…"
    return text


def _title(prompt: str) -> str:
    if not prompt:
        return "Untitled session"
    if prompt.startswith("/"):
        return prompt.split()[0]
    line = prompt.strip().split("\n")[0].strip()
    if len(line) < 4:
        line = prompt.strip().replace("\n", " ").strip()
    return (line[:78] + "…") if len(line) > 80 else line


def _tool_minutes(name: str) -> float:
    if name in TOOL_MINUTES:
        return TOOL_MINUTES[name]
    if name.startswith("mcp__"):
        return 3.0
    return 1.0


def _classify(code_files, doc_files, data_files, mcp, web_hits, tool_count):
    """Return (category, task_type). category drives the 'no code' badge."""
    has_code = code_files > 0
    has_other = (doc_files + data_files + sum(mcp.values()) + web_hits) > 0

    if has_code and has_other:
        category = "mixed"
    elif has_code:
        category = "code"
    else:
        category = "non-code"

    if code_files > 0:
        task = "Code & scripts"
    elif data_files > 0:
        task = "Spreadsheets & data"
    elif mcp["notion"] > 0:
        task = "Docs & notes"
    elif mcp["gmail"] > 0:
        task = "Email"
    elif mcp["calendar"] > 0:
        task = "Scheduling"
    elif doc_files > 0:
        task = "Writing"
    elif web_hits >= 3:
        task = "Research"
    elif tool_count > 0:
        task = "Automation"
    else:
        task = "Thinking & planning"
    return category, task


_PROJECT_MARKERS = {"claude-apps", "projects", "repos", "code", "src", "work", "dev"}


def _project_name(path: str) -> str | None:
    """Best-effort project name from a file path the session touched."""
    parts = Path(path).parts
    for i, seg in enumerate(parts):
        if i + 1 < len(parts) and (seg.lower() in _PROJECT_MARKERS or seg == "skills"):
            return parts[i + 1]
    return parts[-2] if len(parts) >= 2 else None


def _derive_project(touched_paths: list, cwd: str) -> str:
    """Name the project from the files touched (the real work), falling back
    to the working directory. Avoids the launch-folder being mislabelled —
    most sessions launch from $HOME but the work lives in a subdirectory."""
    names = [n for n in (_project_name(p) for p in touched_paths) if n]
    if names:
        return Counter(names).most_common(1)[0][0]
    if cwd:
        return Path(cwd).name or cwd
    return "—"


def parse_session(path: Path) -> Receipt | None:
    """Parse one session JSONL file into a Receipt, or None if it's empty."""
    timestamps = []
    in_tok = out_tok = cc_tok = cr_tok = 0
    seen_req = set()
    hourly: dict = {}
    tool_count = 0
    weighted_minutes = 0.0
    code_files = doc_files = data_files = web_hits = 0
    mcp = {"notion": 0, "gmail": 0, "calendar": 0, "drive": 0}
    files_created: list = []
    touched_paths: list = []
    cwd = ""
    model = ""
    first_user = ""

    try:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not cwd:
                    cwd = obj.get("cwd") or ""

                kind = obj.get("type")
                if kind not in ("user", "assistant"):
                    continue

                dt = _parse_ts(obj.get("timestamp"))
                if dt:
                    timestamps.append(dt)
                msg = obj.get("message") or {}

                if kind == "user":
                    if not first_user:
                        cleaned = _clean_prompt(_extract_text(msg.get("content")))
                        if cleaned:
                            first_user = cleaned
                    continue

                # assistant
                model = msg.get("model") or model
                usage = msg.get("usage")
                rid = obj.get("requestId") or msg.get("id")
                if usage and rid and rid not in seen_req:
                    seen_req.add(rid)
                    i = usage.get("input_tokens") or 0
                    o = usage.get("output_tokens") or 0
                    cc = usage.get("cache_creation_input_tokens") or 0
                    cr = usage.get("cache_read_input_tokens") or 0
                    in_tok += i
                    out_tok += o
                    cc_tok += cc
                    cr_tok += cr
                    if dt:
                        key = dt.astimezone().strftime("%Y-%m-%d %H")
                        hourly[key] = hourly.get(key, 0) + i + o + cc + cr

                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_use":
                            continue
                        tool_count += 1
                        name = block.get("name", "")
                        weighted_minutes += _tool_minutes(name)
                        inp = block.get("input") or {}
                        fp = inp.get("file_path") or inp.get("path") or inp.get("notebook_path")
                        if fp:
                            touched_paths.append(str(fp))
                            ext = Path(str(fp)).suffix.lower()
                            if ext in CODE_EXTS:
                                code_files += 1
                            elif ext in DOC_EXTS:
                                doc_files += 1
                            elif ext in DATA_EXTS:
                                data_files += 1
                            if name == "Write":
                                files_created.append(str(fp))
                        lname = name.lower()
                        if name in ("WebSearch", "WebFetch"):
                            web_hits += 1
                        elif lname.startswith("mcp__"):
                            if "notion" in lname:
                                mcp["notion"] += 1
                            elif "gmail" in lname or "mail" in lname:
                                mcp["gmail"] += 1
                            elif "calendar" in lname:
                                mcp["calendar"] += 1
                            elif "drive" in lname:
                                mcp["drive"] += 1
    except OSError:
        return None

    if not timestamps:
        return None

    start = min(timestamps).astimezone()
    end = max(timestamps).astimezone()
    duration = max(0, int((end - start).total_seconds() // 60))

    category, task_type = _classify(
        code_files, doc_files, data_files, mcp, web_hits, tool_count
    )

    if tool_count == 0:
        # Pure thinking/advice session — still saved you something.
        minutes_saved = min(duration, 25) if duration > 2 else 3
    else:
        minutes_saved = min(SESSION_MINUTES_CAP, max(5, round(weighted_minutes)))

    project = _derive_project(touched_paths, cwd)

    return Receipt(
        session_id=path.stem,
        project=project,
        title=_title(first_user),
        prompt=first_user,
        start=start,
        end=end,
        duration_min=duration,
        model=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_creation_tokens=cc_tok,
        cache_read_tokens=cr_tok,
        tool_count=tool_count,
        files_created=files_created,
        category=category,
        task_type=task_type,
        minutes_saved=minutes_saved,
        hourly=hourly,
    )


def all_session_files():
    """Yield every real session JSONL file (skips sub-agent transcripts)."""
    if not PROJECTS_DIR.exists():
        return
    for proj in PROJECTS_DIR.iterdir():
        if not proj.is_dir():
            continue
        for f in proj.glob("*.jsonl"):
            if f.stem.startswith("agent-"):
                continue
            yield f
