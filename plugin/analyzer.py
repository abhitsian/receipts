"""Receipts — turns a pile of parsed sessions into dashboard data.

The headline metrics here are deliberately *not* raw token count. Tokens are
the fun garnish; tasks done, streak, hours saved, and "X needed no code" are
what changes behaviour and what's legible to a non-coder.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from pathlib import Path

MODEL_LABELS = {
    "opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku",
}


def _model_label(model: str) -> str:
    if not model:
        return "Claude"
    m = model.lower()
    family = next((v for k, v in MODEL_LABELS.items() if k in m), "Claude")
    ver = ""
    import re
    match = re.search(r"(\d+)-(\d+)", m)
    if match:
        ver = f" {match.group(1)}.{match.group(2)}"
    return f"{family}{ver}"


def receipt_dict(r) -> dict:
    """Serialise a Receipt for the frontend."""
    created, seen = [], set()
    for fp in r.files_created:
        base = Path(fp).name
        if base and base not in seen:
            seen.add(base)
            created.append(base)
    return {
        "id": r.session_id,
        "title": r.title,
        "project": r.project,
        "category": r.category,
        "task_type": r.task_type,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "cache_tokens": r.cache_creation_tokens + r.cache_read_tokens,
        "total_tokens": r.total_tokens,
        "tool_count": r.tool_count,
        "minutes_saved": r.minutes_saved,
        "start": r.start.isoformat(),
        "end": r.end.isoformat(),
        "duration_min": r.duration_min,
        "model": _model_label(r.model),
        "prompt": r.prompt,
        "files_created": created[:6],
        "is_active": r.is_active,
    }


def build_dashboard(receipts: list) -> dict:
    now = datetime.now().astimezone()
    today = now.date()
    today_str = today.isoformat()

    # Tokens per local hour, today only — the "burn rate" chart.
    hourly = [0] * 24
    daily: dict = {}
    for r in receipts:
        for key, tok in r.hourly.items():
            day, hr = key.split(" ")
            daily[day] = daily.get(day, 0) + tok
            if day == today_str:
                hourly[int(hr)] += tok

    todays = [r for r in receipts if r.start.date() == today]
    # "no code" celebrates *pure* non-code work only — a mixed session
    # touched code, so it doesn't count toward the recruiting metric.
    today_noncode = sum(1 for r in todays if r.category == "non-code")

    # Streak — consecutive days with at least one session, ending today
    # (or yesterday, if today hasn't started yet).
    active_days = {r.start.date() for r in receipts}
    streak = 0
    cur = today if today in active_days else today - timedelta(days=1)
    while cur in active_days:
        streak += 1
        cur -= timedelta(days=1)

    # 14-day trend.
    day_sessions: dict = {}
    for r in receipts:
        d = r.start.date().isoformat()
        day_sessions[d] = day_sessions.get(d, 0) + 1
    trend = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        trend.append({
            "date": ds,
            "label": d.strftime("%a"),
            "dom": d.day,
            "tokens": daily.get(ds, 0),
            "sessions": day_sessions.get(ds, 0),
            "is_today": ds == today_str,
        })

    recent = sorted(receipts, key=lambda r: r.end, reverse=True)
    active = [receipt_dict(r) for r in recent if r.is_active]
    first_date = min((r.start.date() for r in receipts), default=today)

    return {
        "generated_at": now.isoformat(),
        "today": {
            "tokens": sum(hourly),
            "hourly": hourly,
            "tasks": len(todays),
            "sessions": len(todays),
            "minutes_saved": sum(r.minutes_saved for r in todays),
            "noncode": today_noncode,
        },
        "streak": streak,
        "trend": trend,
        "alltime": {
            "tokens": sum(r.total_tokens for r in receipts),
            "sessions": len(receipts),
            "minutes_saved": sum(r.minutes_saved for r in receipts),
            "noncode": sum(1 for r in receipts if r.category == "non-code"),
            "first_date": first_date.isoformat(),
            "days_active": len(active_days),
        },
        "active": active,
        "receipts": [receipt_dict(r) for r in recent[:60]],
    }


def build_insights(receipts: list, days: int) -> dict:
    """Date-scoped analytics. days=0 means all time.

    Time-series and heatmap use the per-message hourly buckets (accurate to
    when tokens were actually spent). The task/project/model breakdowns
    attribute a whole session's tokens to that session — a session has one
    task type, so that's the honest cut.
    """
    now = datetime.now().astimezone()
    today = now.date()

    if days and days > 0:
        cutoff = today - timedelta(days=days - 1)
    else:
        cutoff = min((r.start.date() for r in receipts), default=today)

    span = (today - cutoff).days + 1
    if span > 120:                       # keep the daily chart readable
        span = 120
        cutoff = today - timedelta(days=119)

    in_range = [r for r in receipts if r.start.date() >= cutoff]

    # Daily series + heatmap — built from the same in-range sessions as the
    # summary, so "tokens over time" and the headline total always agree.
    daily: dict = {}
    heat = [[0] * 24 for _ in range(7)]  # heat[weekday][hour]
    for r in in_range:
        for key, tok in r.hourly.items():
            day_s, hr_s = key.split(" ")
            try:
                d = date.fromisoformat(day_s)
            except ValueError:
                continue
            if d < cutoff or d > today:
                continue
            daily[day_s] = daily.get(day_s, 0) + tok
            heat[d.weekday()][int(hr_s)] += tok

    daily_series = []
    for i in range(span):
        d = cutoff + timedelta(days=i)
        ds = d.isoformat()
        daily_series.append({
            "date": ds,
            "label": d.strftime("%-d %b"),
            "dow": d.strftime("%a"),
            "tokens": daily.get(ds, 0),
        })

    def agg(key_fn):
        m: dict = {}
        for r in in_range:
            slot = m.setdefault(key_fn(r), [0, 0])
            slot[0] += r.total_tokens
            slot[1] += 1
        total = sum(v[0] for v in m.values()) or 1
        rows = [{"name": k, "tokens": v[0], "sessions": v[1],
                 "pct": round(v[0] / total * 100)} for k, v in m.items()]
        return sorted(rows, key=lambda x: x["tokens"], reverse=True)

    category = {"code": 0, "non-code": 0, "mixed": 0}
    for r in in_range:
        category[r.category] = category.get(r.category, 0) + r.total_tokens

    return {
        "days": days,
        "label": f"Last {days} days" if days else "All time",
        "total_tokens": sum(r.total_tokens for r in in_range),
        "total_sessions": len(in_range),
        "total_saved": sum(r.minutes_saved for r in in_range),
        "active_days": len({r.start.date() for r in in_range}),
        "daily": daily_series,
        "heatmap": heat,
        "by_task": agg(lambda r: r.task_type),
        "by_project": agg(lambda r: r.project)[:10],
        "by_model": agg(lambda r: _model_label(r.model)),
        "by_category": category,
    }
