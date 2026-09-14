#!/usr/bin/env python3
"""Bake today's lake-day score into today/index.html's static HTML.

Why this exists: /today/ computes its score entirely client-side from live
NWS + Duke fetches. Google's renderer has a limited budget for waiting on
JS + network, and was snapshotting the page mid-skeleton — "Crawled -
currently not indexed" in Search Console, because there was no real content
to index. This script is a faithful Python port of the same scoring logic
in today/index.html's <script> (windMax/sunsetFor/stormWindow/scoreDay/
verdictLine) and writes its output into marker-delimited spots in the
static markup, so a crawler that never runs JS still sees a real score,
verdict, and "why" reasoning. Real visitors still get the live client-side
version on top of it — this only changes what's there before JS runs.

Run by .github/workflows/today-log.yml on a schedule. Exits 0 without
writing if the APIs are unreachable, so the workflow only commits when
there's something real to bake.
"""
import json, math, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - stdlib since 3.9
    ET = timezone.utc

FC = "https://api.weather.gov/gridpoints/GSP/45,41/forecast"
DUKE = "https://api.hydro-derived.duke-energy.app/lakes/current-level"
ROOT = os.path.join(os.path.dirname(__file__), "..")
PAGE = os.path.join(ROOT, "today", "index.html")
UA = "keowee.club (contact: clubkeowee@gmail.com)"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/geo+json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def replace_between(text, start, end, body):
    """Swap the content between two marker comments. No-op if either marker
    is missing, so a future page edit can never corrupt the file or crash."""
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        return text
    return text[: i + len(start)] + body + text[j:]


# ---------- ported from today/index.html's inline <script> ----------

def wind_max(s):
    m = re.search(r"(\d+)(?:\s*to\s*(\d+))?\s*mph", s or "")
    if not m:
        return None
    return int(m.group(2) or m.group(1))


def sunset_for(date):
    """NOAA solar approximation, same formula as sunsetFor() in the page JS."""
    lat = 34.85 * math.pi / 180
    lng = -82.93
    doy = date.timetuple().tm_yday
    g = 2 * math.pi / 365 * (doy - 1)
    eqt = 229.18 * (
        0.000075
        + 0.001868 * math.cos(g)
        - 0.032077 * math.sin(g)
        - 0.014615 * math.cos(2 * g)
        - 0.040849 * math.sin(2 * g)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(g)
        + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g)
        + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g)
        + 0.00148 * math.sin(3 * g)
    )
    ha = math.acos(
        math.cos(90.833 * math.pi / 180) / (math.cos(lat) * math.cos(decl))
        - math.tan(lat) * math.tan(decl)
    )
    set_utc_minutes = 720 - 4 * (lng - ha * 180 / math.pi) - eqt
    base = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    d = base + timedelta(minutes=set_utc_minutes)
    local = d.astimezone(ET)
    hour12 = local.hour % 12 or 12
    return f"{hour12}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"


def local_day(dt):
    return dt.astimezone(ET).strftime("%Y-%m-%d")


def local_hour(dt):
    return int(dt.astimezone(ET).strftime("%H"))


def fmt_hour_label(dt):
    local = dt.astimezone(ET)
    hour12 = local.hour % 12 or 12
    return f"{hour12} {'AM' if local.hour < 12 else 'PM'}"


def storm_window(hourly, ref_date):
    if not hourly:
        return None
    day = local_day(ref_date)
    hrs = [h for h in hourly if local_day(datetime.fromisoformat(h["startTime"])) == day
           and 8 <= local_hour(datetime.fromisoformat(h["startTime"])) <= 22]
    if len(hrs) < 4:
        return None
    pops = [(h.get("probabilityOfPrecipitation") or {}).get("value") or 0 for h in hrs]
    peak = max(pops)
    if peak < 35:
        return None
    th = max(30, peak * 0.6)
    first = pops.index(peak)
    last = first
    while first > 0 and pops[first - 1] >= th:
        first -= 1
    while last < len(pops) - 1 and pops[last + 1] >= th:
        last += 1
    start_dt = datetime.fromisoformat(hrs[first]["startTime"])
    end_dt = datetime.fromisoformat(hrs[last]["startTime"]) + timedelta(hours=1)
    start_h = local_hour(start_dt)
    end_h = local_hour(datetime.fromisoformat(hrs[last]["startTime"])) + 1
    if first == 0 and last == len(pops) - 1:
        return {"label": "on and off all day", "allDay": True}
    return {
        "label": f"mainly {fmt_hour_label(start_dt)} to {fmt_hour_label(end_dt)}",
        "allDay": False,
        "startH": start_h,
        "endH": end_h,
    }


def score_day(p, down_ft, sw):
    s = 10.0
    why = []
    rain = (p.get("probabilityOfPrecipitation") or {}).get("value") or 0
    wind = wind_max(p.get("windSpeed")) or 0
    t = p["temperature"]
    when = (", " + sw["label"]) if sw else ""
    hint = " Watch the radar."
    if sw and not sw["allDay"]:
        if sw["startH"] >= 12:
            hint = " The morning is your window."
        elif sw["endH"] <= 13:
            hint = " The afternoon opens up."
        else:
            hint = " Work the edges of it."
    if rain >= 60:
        s -= 4
        why.append(f"<b>Storms likely</b> ({rain}%){when}.{hint}")
    elif rain >= 40:
        s -= 2.5
        why.append(f"<b>Rain possible</b> ({rain}%){when}." + (hint if sw else " Keep a window open."))
    elif rain >= 20:
        s -= 1
        why.append(f"<b>Slight rain chance</b> ({rain}%{when if sw and not sw['allDay'] else ''}). Probably fine.")
    else:
        why.append(f"<b>Dry</b>. Rain chance just {rain}%.")
    if wind > 20:
        s -= 4
        why.append(f"<b>Windy</b>: gusts to {wind} mph. Rough water, sailors only.")
    elif wind > 14:
        s -= 2.5
        why.append(f"<b>Breezy</b>: up to {wind} mph. Chop on open water.")
    elif wind > 8:
        s -= 1
        why.append(f"<b>Light chop</b>: wind to {wind} mph.")
    else:
        why.append(f"<b>Calm water</b>: wind under {max(wind, 5)} mph.")
    if t < 60:
        s -= 4
        why.append(f"<b>Cold</b>: {t}°. Wetsuit weather.")
    elif t < 70:
        s -= 2
        why.append(f"<b>Cool</b>: {t}°. Bring a layer.")
    elif t > 95:
        s -= 1
        why.append(f"<b>Scorcher</b>: {t}°. The water is the only place to be.")
    else:
        why.append(f"<b>{t}°</b> and comfortable.")
    if down_ft is not None:
        if down_ft > 4:
            s -= 1
            why.append(f"<b>Lake is low</b>: {down_ft:.1f} ft below full. Mind shallow ramps.")
        else:
            why.append(f"<b>Water is fine</b>: {down_ft:.1f} ft below full pond.")
    s = max(1.0, min(10.0, round(s * 2) / 2))
    return {"s": s, "why": why, "rain": rain, "wind": wind, "t": t}


def verdict_line(s, p):
    if s >= 9:
        return "Go. Days like this are why you live here."
    if s >= 7.5:
        return f"A proper lake day. {p.get('shortForecast', '')}."
    if s >= 5.5:
        return "Decent. Pick your window and keep an eye up."
    if s >= 3.5:
        return "Iffy out there. The brave get the lake to themselves."
    return "Not today. The lake will forgive you."


def fmt_score(s):
    return f"{s:.1f}" if s % 1 else str(int(s))


def fmt_day_heading(name, dt):
    local = dt.astimezone(ET)
    return f"{name} · {local.strftime('%b')} {local.day}"


# ---------- page patching ----------

def patch_page(hero, hs, sw, down_ft):
    if not os.path.exists(PAGE):
        return False
    html = original = open(PAGE, encoding="utf-8").read()

    grade = "great" if hs["s"] >= 7.5 else "ok" if hs["s"] >= 5 else "bad"
    tag = (
        f'<section class="verdict" id="verdict" aria-label="Today\'s lake day score" data-grade="{grade}">'
    )
    html = replace_between(html, "<!-- today-grade:start -->", "<!-- today-grade:end -->", tag)

    hero_dt = datetime.fromisoformat(hero["startTime"])
    html = replace_between(html, "<!-- today-day:start -->", "<!-- today-day:end -->",
                            fmt_day_heading(hero["name"], hero_dt))
    html = replace_between(html, "<!-- today-score:start -->", "<!-- today-score:end -->", fmt_score(hs["s"]))
    html = replace_between(html, "<!-- today-line:start -->", "<!-- today-line:end -->",
                            verdict_line(hs["s"], hero))

    stats = [("\U0001F321", f"<b>{hero['temperature']}°</b>"),
             ("\U0001F4A8", f"wind <b>{hs['wind'] or '—'} mph</b>"),
             ("\U0001F327", f"rain <b>{hs['rain']}%</b>")]
    if down_ft is not None:
        stats.append(("\U0001F30A", f"water <b>−{down_ft:.1f} ft</b>"))
    stats.append(("\U0001F305", f"sunset <b>{sunset_for(hero_dt)}</b>"))
    stats_html = "".join(f'<span class="vstat">{icon} {label}</span>' for icon, label in stats)
    html = replace_between(html, "<!-- today-stats:start -->", "<!-- today-stats:end -->", stats_html)

    why_html = "".join(f"<li>{w}</li>" for w in hs["why"])
    html = replace_between(html, "<!-- today-why:start -->", "<!-- today-why:end -->", why_html)

    desc = (
        f"Today's lake day score for Lake Keowee is {fmt_score(hs['s'])}/10 — "
        f"{verdict_line(hs['s'], hero)} {hero['temperature']}°, rain {hs['rain']}%, "
        f"wind up to {hs['wind'] or 0} mph. Updated continuously from the NWS forecast and Duke Energy's gauge."
    )
    html = replace_between(html, "<!-- today-desc:start -->", "<!-- today-desc:end -->",
                            f'<meta name="description" content="{desc}">')

    if html == original:
        return False
    open(PAGE, "w", encoding="utf-8").write(html)
    return True


def main():
    try:
        forecast = fetch_json(FC)
        hourly = fetch_json(FC + "/hourly")["properties"]["periods"]
    except Exception as e:
        print(f"forecast api unavailable, skipping: {e}")
        return 0

    periods = forecast["properties"]["periods"]
    daytime = [p for p in periods if p.get("isDaytime")]
    if not daytime:
        print("no daytime period found, skipping")
        return 0
    hero = daytime[0]

    down_ft = None
    try:
        lakes = fetch_json(DUKE)
        k = next((l for l in lakes if l.get("LakeName") == "KEOWEE"), None)
        actual = k and float(k["Actual"])
        if actual and not math.isnan(actual):
            down_ft = max(0.0, round(100 - actual, 1))
    except Exception as e:
        print(f"duke api unavailable, scoring without water level: {e}")

    sw = storm_window(hourly, datetime.fromisoformat(hero["startTime"]))
    hs = score_day(hero, down_ft, sw)

    if patch_page(hero, hs, sw, down_ft):
        print(f"baked today score {fmt_score(hs['s'])}/10 for {hero['name']}")
    else:
        print("no change (score/verdict unchanged since last run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
