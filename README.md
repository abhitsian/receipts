# 🧾 Receipts

See and share what you've done with Claude Code — a local dashboard (tokens,
streak, hours saved, what's running now, date-range insights) plus
screenshot-ready receipt cards and share links for Slack and Teams.

This repository is a **Claude Code plugin marketplace**. Receipts installs in two
commands and runs entirely on your machine — nothing is uploaded.

## The tokenmaxxing craze

In early 2026, "tokenmaxxing" took off — deliberately burning more AI tokens to
look more productive. Companies stood up token leaderboards, managers started
asking "how many tokens did you burn this week," and engineers admitted padding
the number to climb the rankings. The backlash came fast: token volume is a
vanity metric, trivial to game and barely connected to real output. Meta
launched a leaderboard, then quietly retired it.

Receipts is built for that moment — and the name is the whole idea: **keep the
receipts.** When someone asks how many tokens you've burned, you can show them
exactly where they went. Receipts lets you:

- **Monitor** your usage — live token burn by the hour, and the sessions running right now
- **Get insights** — what you actually spend tokens on, by task, by project, by day, by hour
- **Show it off** — turn a day or a session into a receipt card that proves the work behind the spend

### Further reading on tokenmaxxing

- [The Pulse: 'Tokenmaxxing' as a weird new trend](https://blog.pragmaticengineer.com/the-pulse-tokenmaxxing-as-a-weird-new-trend/) — The Pragmatic Engineer
- [Tokenmaxxing is making developers less productive than they think](https://techcrunch.com/2026/04/17/tokenmaxxing-is-making-developers-less-productive-than-they-think/) — TechCrunch
- [Tokenmaxxing and the search for AI metrics that matter](https://leaddev.com/ai/tokenmaxxing-and-the-search-for-ai-metrics-that-matter) — LeadDev
- [Big Tech has a tokenmaxxing habit](https://www.tomshardware.com/tech-industry/big-tech/big-tech-has-a-tokenmaxxing-habit) — Tom's Hardware
- [Clawdmeter turns your Claude Code usage stats into a tiny desktop dashboard](https://techcrunch.com/2026/05/14/clawdmeter-turns-your-claude-code-usage-stats-into-a-tiny-desktop-dashboard/) — TechCrunch

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
