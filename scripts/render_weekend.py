#!/usr/bin/env python3
"""Render the current This Weekend edition from data/weekend.json."""

from __future__ import annotations

import html
import json
import pathlib
import sys


ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SOURCE = ROOT / "data" / "weekend.json"
OUTPUT = ROOT / "weekend" / "index.html"
HOME = ROOT / "index.html"
HOME_START = "<!-- weekend:start -->"
HOME_END = "<!-- weekend:end -->"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def event_card(event: dict) -> str:
    return f"""    <article class="event">
      <p class="event-meta"><span>{esc(event["day"])} · {esc(event["date_display"])}</span><span>{esc(event["tag"])}</span></p>
      <h3>{esc(event["title"])}</h3>
      <p class="event-body">{esc(event["body"])}</p>
      <p class="event-note">{esc(event["note"])}</p>
      <a class="event-link" href="{esc(event["url"])}" target="_blank" rel="noopener">Check details &amp; availability ↗</a>
    </article>"""


def plan_card(item: dict) -> str:
    external = ' target="_blank" rel="noopener"' if item.get("external") else ""
    return f"""    <article class="plan-card">
      <p class="plan-day">{esc(item["day"])}</p>
      <h3>{esc(item["title"])}</h3>
      <p>{esc(item["body"])}</p>
      <a class="plan-link" href="{esc(item["url"])}"{external}>{esc(item["label"])}</a>
    </article>"""


def home_teaser(edition: dict) -> str:
    return f"""<section class="weekend-tease" aria-labelledby="weekend-tease-title">
  <div class="weekend-tease-inner">
    <div>
      <p class="eyebrow">This weekend · {esc(edition["date_display"])}</p>
      <h2 id="weekend-tease-title">Two reasons to go <em>north.</em></h2>
    </div>
    <div>
      <p>{esc(edition["dek"])}</p>
      <a class="see-all" href="/weekend/">Open the weekend plan <i>→</i></a>
    </div>
  </div>
</section>"""


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    before, marker, remainder = text.partition(start)
    if not marker:
        raise ValueError(f"missing marker {start}")
    _, marker, after = remainder.partition(end)
    if not marker:
        raise ValueError(f"missing marker {end}")
    return f"{before}{start}\n{replacement}\n{end}{after}"


def schema(edition: dict) -> str:
    events = []
    for item in edition["events"]:
        events.append(
            {
                "@type": "Event",
                "name": item["title"],
                "startDate": item["date"],
                "endDate": item["date"],
                "image": "https://keowee.club/og.png",
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "location": {
                    "@type": "Place",
                    "name": item["tag"],
                    "address": {
                        "@type": "PostalAddress",
                        "addressRegion": "SC",
                        "addressCountry": "US",
                    },
                },
                "description": item["body"],
                "url": item["url"],
                "organizer": {"@type": "Organization", "name": item["source"], "url": item["url"]},
            }
        )
    graph = [
        {
            "@type": "WebPage",
            "@id": "https://keowee.club/weekend/#page",
            "url": "https://keowee.club/weekend/",
            "name": edition["title"],
            "description": edition["dek"],
            "dateModified": edition["updated"],
            "isPartOf": {"@id": "https://keowee.club/#website"},
        },
        {
            "@type": "ItemList",
            "name": f'Events around Lake Keowee and Lake Jocassee, {edition["date_display"]}',
            "itemListElement": [
                {"@type": "ListItem", "position": index, "item": event}
                for index, event in enumerate(events, 1)
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False).replace("</", "<\\/")


def render(edition: dict) -> str:
    events = "\n".join(event_card(item) for item in edition["events"])
    plan = "\n".join(plan_card(item) for item in edition["plan"])
    sources = "\n".join(
        f'      <li><a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["label"])}</a></li>'
        for item in edition["sources"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>This Weekend on Lake Keowee &amp; Lake Jocassee — {esc(edition["date_display"])} | keowee.club</title>
<meta name="description" content="{esc(edition["dek"])}">
<link rel="canonical" href="https://keowee.club/weekend/">
<meta name="theme-color" content="#0A3A34">
<link rel="icon" type="image/png" sizes="512x512" href="/favicon.png?v=2">
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2">
<meta property="og:type" content="website">
<meta property="og:site_name" content="keowee.club">
<meta property="og:title" content="This Weekend on Keowee + Jocassee">
<meta property="og:description" content="{esc(edition["dek"])}">
<meta property="og:url" content="https://keowee.club/weekend/">
<meta property="og:image" content="https://keowee.club/weekend/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="This Weekend on Keowee + Jocassee">
<meta name="twitter:description" content="{esc(edition["dek"])}">
<meta name="twitter:image" content="https://keowee.club/weekend/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&amp;family=Instrument+Sans:wght@400;500;600&amp;family=Space+Mono:wght@400;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/weekend.css">
<script type="application/ld+json">
{schema(edition)}
</script>
</head>
<body>
<nav class="nav" aria-label="Main">
  <div class="nav-inner">
    <a class="wordmark" href="/" aria-label="Keowee Club home">
      <img class="pennant-logo" src="../brand/keoweeclub.svg" alt="Keowee Club" width="383" height="312">
    </a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/guides/lake-keowee-first-timer/">Guides</a></li>
      <li><a href="/eat-and-drink/">Eat &amp; Drink</a></li>
      <li><a href="/map/">Map</a></li>
      <li><a href="/lake-level/">Lake Level</a></li>
      <li><a href="/depth/">Depth</a></li>
    </ul>
    <a class="nav-cta" href="#dispatch">Get the Dispatch</a>
  </div>
</nav>

<header class="hero">
  <div class="hero-inner">
    <p class="crumb"><a href="/">Keowee Club</a> &nbsp;→&nbsp; This Weekend</p>
    <p class="eyebrow">{esc(edition["date_display"])}</p>
    <h1>This weekend <em>on the lakes.</em></h1>
    <p class="dek">{esc(edition["dek"])}</p>
    <p class="edition"><span>Updated {esc(edition["updated_display"])}</span><span>Keowee + Jocassee</span><span>Locally edited</span></p>
  </div>
  <svg class="hero-wave" viewBox="0 0 1440 60" preserveAspectRatio="none" aria-hidden="true"><path d="M0 30C180 60 360 0 540 20s360 40 540 15 300-25 360-10V60H0Z" fill="#EFF8F3"/></svg>
</header>

<section class="conditions" aria-label="Live lake conditions">
  <article class="condition"><a href="https://forecast.weather.gov/MapClick.php?lat=34.85&amp;lon=-82.93"><span>Weather</span><strong id="weather">Checking the sky…</strong></a></article>
  <article class="condition"><a href="/lake-level/"><span>Keowee</span><strong id="keowee">Checking the gauge…</strong></a></article>
  <article class="condition"><a href="/lake-level/"><span>Jocassee</span><strong id="jocassee">Checking the gauge…</strong></a></article>
  <article class="condition"><span>Sunset</span><strong id="sunset">This evening</strong></article>
</section>

<main>
  <section aria-labelledby="events-title">
    <div class="section-head"><h2 id="events-title">Worth leaving the cove for</h2><span>{len(edition["events"])} verified picks</span></div>
    <p class="section-intro">A short list on purpose. Availability and weather can move faster than this page, so check the organizer before pointing the car north.</p>
    <div class="events">
{events}
    </div>
  </section>

  <section class="plan-section" aria-labelledby="plan-title">
    <div class="section-head"><h2 id="plan-title">Steal this weekend</h2><span>Three days · no heroics</span></div>
    <p class="section-intro">One useful idea per day. Add friends, subtract obligations, and do not try to circumnavigate Keowee before lunch.</p>
    <div class="plan">
{plan}
    </div>
  </section>

  <aside class="local-note">
    <strong>Before you go</strong>
    Check the forecast, lake level, booking status, and park entry details directly. Live data on this page fails back to plain language if a third-party service is unavailable; it should never be the only thing standing between you and a safe call.
  </aside>

  <section class="sources">
    <h2>Sources checked for this edition</h2>
    <ul>
{sources}
    </ul>
  </section>
</main>

<section class="dispatch" id="dispatch">
  <div class="dispatch-inner">
    <p class="eyebrow">Thursday afternoon · Zero spam · All lake</p>
    <h2>Get next weekend <em>before Friday.</em></h2>
    <p>Fresh conditions, a few plans worth making, and the occasional hot take about pontoon etiquette. Free, weekly, unsubscribe whenever.</p>
    <form id="signup" action="https://buttondown.com/api/emails/embed-subscribe/keowee" method="post" target="bd-frame" novalidate>
      <input type="email" id="email" name="email" placeholder="you@somewhere.com" aria-label="Email address" required>
      <input type="hidden" name="embed" value="1">
      <button type="submit">Send the Thursday note</button>
    </form>
    <iframe name="bd-frame" title="Newsletter signup" style="display:none" aria-hidden="true"></iframe>
    <p class="success" id="success">🌊 You're in. See you Thursday.</p>
    <p class="fine">One useful lake email a week during the season.</p>
  </div>
</section>

<footer>
  <div class="foot-marks" aria-hidden="true"><img src="../brand/footer-marks.svg" alt="" loading="lazy" width="329" height="140"></div>
  <div class="foot-inner">
    <span>© 2026 keowee.club</span>
    <span>Made on the dock 🛥️</span>
    <a href="/contact/">Contact</a>
    <a href="/">Home ↑</a>
  </div>
</footer>

<script>
(function(){{
  function text(id,value){{document.getElementById(id).textContent=value;}}
  function levelVerdict(value){{
    if(value>=97)return 'basically full pond';
    if(value>=95)return 'plenty of water';
    if(value>=93.5)return 'holding steady';
    return 'running low — plan the launch';
  }}
  fetch('https://api.hydro-derived.duke-energy.app/lakes/current-level')
    .then(function(response){{if(!response.ok)throw 0;return response.json();}})
    .then(function(lakes){{
      [['KEOWEE','keowee'],['JOCASSEE','jocassee']].forEach(function(pair){{
        var lake=lakes.find(function(item){{return item.LakeName===pair[0];}});
        var value=lake&&parseFloat(lake.Actual);
        if(value&&!isNaN(value))text(pair[1],(Math.round(value*10)/10)+'% · '+levelVerdict(value));
      }});
    }}).catch(function(){{text('keowee','Level unavailable');text('jocassee','Level unavailable');}});
  fetch('https://api.weather.gov/stations/KCEU/observations/latest')
    .then(function(response){{if(!response.ok)throw 0;return response.json();}})
    .then(function(observation){{
      var properties=observation.properties,c=properties.temperature&&properties.temperature.value;
      var degrees=c==null?'':Math.round(c*9/5+32)+'°';
      text('weather',[(properties.textDescription||'').trim(),degrees].filter(Boolean).join(' · ')||'Open the NWS forecast');
    }}).catch(function(){{text('weather','Open the NWS forecast');}});
  function sunset(lat,lng,date){{
    var rad=Math.PI/180,deg=180/Math.PI,start=Date.UTC(date.getUTCFullYear(),0,0);
    var day=Math.floor((Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),date.getUTCDate())-start)/86400000);
    var lngHour=lng/15,time=day+((18-lngHour)/24),mean=(0.9856*time)-3.289;
    var longitude=(mean+(1.916*Math.sin(mean*rad))+(0.020*Math.sin(2*mean*rad))+282.634+360)%360;
    var ascension=deg*Math.atan(0.91764*Math.tan(longitude*rad));ascension=(ascension+360)%360;
    ascension=(ascension+((Math.floor(longitude/90)*90)-(Math.floor(ascension/90)*90)))/15;
    var sinDec=0.39782*Math.sin(longitude*rad),cosDec=Math.cos(Math.asin(sinDec));
    var cosH=(Math.cos(90.833*rad)-(sinDec*Math.sin(lat*rad)))/(cosDec*Math.cos(lat*rad));
    if(cosH>1||cosH<-1)return null;
    var hour=deg*Math.acos(cosH)/15,local=((((hour+ascension-(0.06571*time)-6.622)-lngHour)%24)+24)%24;
    var whole=Math.floor(local),minutes=Math.round((local-whole)*60);if(minutes===60){{whole=(whole+1)%24;minutes=0;}}
    return new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),date.getUTCDate(),whole,minutes));
  }}
  try{{var result=sunset(34.85,-82.93,new Date());if(result)text('sunset',result.toLocaleTimeString('en-US',{{hour:'numeric',minute:'2-digit',timeZone:'America/New_York'}}).toLowerCase());}}catch(error){{}}
  var form=document.getElementById('signup');
  form.addEventListener('submit',function(event){{
    var email=document.getElementById('email');
    if(!email.value||!email.value.includes('@')){{event.preventDefault();email.focus();email.style.borderColor='#FF6E52';return;}}
    form.style.display='none';document.getElementById('success').style.display='block';
  }});
}})();
</script>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "6ffce0786eb54943b7422d812178fe84"}}'></script>
<script defer src="https://cloud.umami.is/script.js" data-website-id="293cc55f-258d-4388-953c-41b49d0dd6ca"></script>
</body>
</html>
"""


def main() -> int:
    data = json.loads(SOURCE.read_text())
    edition = data["edition"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(edition))
    HOME.write_text(replace_between(HOME.read_text(), HOME_START, HOME_END, home_teaser(edition)))
    print(f"rendered weekend edition: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
