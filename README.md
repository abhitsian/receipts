# 🧾 Receipts

See and share what you've done with Claude Code — a local dashboard (tokens,
streak, hours saved, what's running now, date-range insights) plus
screenshot-ready receipt cards and share links for Slack and Teams.

This repository is a **Claude Code plugin marketplace**. Receipts installs in two
commands and runs entirely on your machine — nothing is uploaded.

## Install

In Claude Code:

```
/plugin marketplace add abhitsian/receipts
/plugin install receipts@receipts
```

Then open it any time with:

```
/receipts:open
```

The first launch sets up a local Python environment and starts the dashboard at
http://localhost:4830. Receipts only reads `~/.claude/projects` — your local
Claude Code history — and serves on localhost.

> Don't have Claude Code yet? Get it at <https://claude.com/code>, then run the
> two commands above.

## What it does

- **Dashboard** — tokens burned today by the hour, streak, hours saved, and the
  sessions running right now.
- **Insights** — tokens over time, by task type, by project, a day×hour heatmap,
  and a code vs. no-code split, across 7 / 30 / 90 days or all time.
- **Receipt cards** — turn any session (or your whole day) into a thermal-receipt
  card. Every field is editable, so you scrub anything sensitive before sharing.
- **Share links** — turn a card into a URL. Whoever opens it sees the card and a
  two-step path to install Receipts themselves. The card data is encoded into the
  link itself — no server, no database, nothing stored.

## Repository layout

| Path | What it is |
|---|---|
| `.claude-plugin/marketplace.json` | The marketplace catalog |
| `plugin/` | The Receipts plugin — the app and the `/receipts:open` skill |
| `plugin/README.md` | How the app itself works |
| `docs/` | The static share / adoption page (served via GitHub Pages) |

## Run the app directly

Without the plugin:

```
cd plugin
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
