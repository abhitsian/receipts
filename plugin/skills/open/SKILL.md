---
description: Open Receipts — a local dashboard showing what you've done with Claude Code (tokens, streak, hours saved, what's running now) with shareable receipt cards. Use when the user runs /receipts:open or asks to see their Claude Code usage or make a shareable receipt.
disable-model-invocation: true
allowed-tools: Bash
---

# Open Receipts

Launch the Receipts dashboard for the user. Receipts is a local web app that reads
`~/.claude/projects` and shows tokens, streaks, hours saved, what's running now,
and generates shareable receipt cards.

The app is bundled at `${CLAUDE_PLUGIN_ROOT}`. Run these steps:

1. **Is it already running?** Run:
   `curl -s -o /dev/null -w "%{http_code}" http://localhost:4830/`
   If the output is `200`, Receipts is already up — skip to step 4.

2. **Make sure the Python environment works.** Run:
   `"${CLAUDE_PLUGIN_ROOT}/.venv/bin/python" -c "import fastapi, uvicorn"`
   If that command fails for any reason — no `.venv`, or a `.venv` copied from
   another path with broken absolute paths — rebuild it from scratch:
   - `rm -rf "${CLAUDE_PLUGIN_ROOT}/.venv"`
   - `python3 -m venv "${CLAUDE_PLUGIN_ROOT}/.venv"`. If that fails (some
     Python 3.14 builds fail `ensurepip`), retry with `python3.13`.
   - `"${CLAUDE_PLUGIN_ROOT}/.venv/bin/pip" install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"`

3. **Start the server in the background** (it is a long-running process):
   `"${CLAUDE_PLUGIN_ROOT}/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/app.py"`
   Give it ~3 seconds to come up.

4. **Open the browser:** `open http://localhost:4830` on macOS, or
   `xdg-open http://localhost:4830` on Linux.

5. **Tell the user:** Receipts is running at http://localhost:4830. The first
   launch indexes their Claude Code history in the background and fills in over
   ~30 seconds.

Notes:
- Everything stays local. Receipts only reads `~/.claude/projects` and serves on
  localhost — nothing is uploaded.
- If the port is already in use, Receipts is already running; just open the browser.
