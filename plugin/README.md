# 🧾 Receipts

Track and share what you actually did with Claude Code.

Receipts reads your local Claude Code logs and turns them into a dashboard:
tokens burned by the hour, a usage streak, hours saved, and a feed of every
session. Click any session to mint a **receipt card** — a thermal-receipt-styled
image, sized for Slack and Teams, that shows what you did in plain English
along with the prompt you used.

## Why this exists

"How many tokens are you burning?" is becoming a real — and bad — question from
managers. Receipts answers it with substance instead of a number: *here is the
work behind the tokens.* And because the receipt card carries the prompt, a
teammate who sees it can copy what you did. Showing off becomes teaching.

The headline metrics are tasks done, streak, hours saved, and how many things
needed **no code at all** — because the point is to show non-coders that their
daily work (writing, spreadsheets, research, planning) is Claude Code work too.
Tokens are the fun garnish, not the score.

## Run

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Then open <http://localhost:4830>. In Claude Desk, just launch it — the
`.claude-app.json` manifest handles install and start automatically.

## What it reads

Only `~/.claude/projects/**/*.jsonl` — the logs Claude Code already writes on
your machine. Nothing is uploaded. A receipt leaves your machine only when you
copy a card and paste it somewhere yourself.

## How to share

1. Click any session in **Your receipts**, or hit **Today's receipt**.
2. **Copy as image** → paste straight into a Slack or Teams message.
3. The prompt is printed on the card on purpose — that is how a teammate
   reproduces what you did.

## Notes on the numbers

- A session counts as **running now** if its log file was touched in the last
  10 minutes.
- **Time saved** is a deliberately conservative estimate derived from tool
  activity. It is labelled an estimate everywhere on purpose — over-claiming
  here would poison the tool's credibility.
- Token totals include cache tokens (cache reads + cache creation), which are
  90%+ of real usage. Tools that count only `input_tokens + output_tokens`
  undercount by roughly 100x once prompt caching is on.

## Roadmap

- macOS menu-bar widget — live tokens/hour without opening the dashboard.
- Opt-in team view — patterns across a team, never a rank-ordered leaderboard.
