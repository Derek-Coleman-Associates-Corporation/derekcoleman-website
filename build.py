#!/usr/bin/env python3
"""build.py — static site generator for derekcoleman.com.

Premium single-page portfolio (dark theme) for Derek Coleman — CEO,
Distinguished Engineer, Enterprise Architect, AI Innovator. Same
architecture as the dcassociatesgroup-website generator: stdlib-only,
writes the deployable site to public/, deployed by GitHub Actions →
Azure Static Web Apps.

Sections: hero · expertise tabs · code vault · discussions · contact.
Subpages: /pay (fintech payment cards), 404.

Usage: python3 build.py
"""
from __future__ import annotations

import datetime
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
PUB = ROOT / "public"

SITE = "https://derekcoleman.com"
CONTACT_EMAIL = "derek@derekcoleman.com"
COMPANY_SITE = "https://www.dcassociatesgroup.com"
LINKEDIN = "https://www.linkedin.com/company/derek-coleman-associates-group-inc"
GITHUB_ORG = "https://github.com/Derek-Coleman-Associates-Corporation"

esc = html.escape

SITEMAP_PATHS: list[str] = []

# ─── payments / fintech links (/pay) ─────────────────────────────────────────
# ⚠️ PLACEHOLDER HANDLES — every url below with "YOUR" in it must be replaced
# with the operator's real handle before this page ships to production.
# handle=None ⇒ the card renders with a "handle pending" badge and no link.
PAYMENTS = [
    {"name": "Cash App", "abbr": "$", "color": "#00d632",
     "url": "https://cash.app/$YOURCASHTAG", "handle": None,
     "note": "Instant P2P payments via cashtag."},
    {"name": "Venmo", "abbr": "V", "color": "#008cff",
     "url": "https://venmo.com/u/YOURVENMO", "handle": None,
     "note": "P2P payments and splits."},
    {"name": "PayPal", "abbr": "P", "color": "#3b6fc9",
     "url": "https://paypal.me/YOURPAYPAL", "handle": None,
     "note": "Cards accepted; buyer/seller protection."},
    {"name": "Zelle", "abbr": "Z", "color": "#6d1ed4",
     "url": None, "handle": None,
     "note": "Bank-to-bank transfer — enrollment email/phone shared on request."},
    {"name": "Apple Cash", "abbr": "", "color": "#555555",
     "url": None, "handle": None,
     "note": "In Messages / Wallet — available on request."},
    {"name": "Wise", "abbr": "W", "color": "#9fe870",
     "url": "https://wise.com/pay/me/YOURWISE", "handle": None,
     "note": "International transfers in 40+ currencies."},
]

# ─── design system ────────────────────────────────────────────────────────────
# Dark-first premium theme: deep charcoal, navy accents, slate borders,
# diamond-grid background, Outfit (display) + Inter (body).

CSS = """
:root{
  --bg:#121214; --bg2:#17171b; --card:#1a1a20; --card2:#1e1e26;
  --border:#2a2d36; --border2:#363b47;
  --fg:#e8eaf0; --muted:#9aa3b2; --faint:#6b7280;
  --navy:#1d3a6e; --navy2:#274b8f; --accent:#6ea8ff; --accent2:#8fbcff;
  --green:#7dd3a0; --orange:#e8b26d; --red:#f28b82;
  --tok-k:#7aa2f7; --tok-s:#9ece6a; --tok-c:#565f89; --tok-n:#e0af68; --tok-f:#c3a6ff;
  --radius:14px;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 12px 32px rgba(0,0,0,.35);
  --ease:cubic-bezier(.22,.61,.36,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;scroll-padding-top:84px}
body{
  font:16px/1.7 "Inter","Segoe UI",-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased;
  background-image:
    linear-gradient(45deg,rgba(148,163,184,.045) 1px,transparent 1px),
    linear-gradient(-45deg,rgba(148,163,184,.045) 1px,transparent 1px);
  background-size:34px 34px;
}
h1,h2,h3,.brand{font-family:"Outfit","Inter","Segoe UI",sans-serif}
a{color:var(--accent);text-decoration:none;transition:color .18s var(--ease)}
a:hover{color:var(--accent2)}
img{max-width:100%;height:auto}
.wrap{max-width:1100px;margin:0 auto;padding:0 1.4rem}
section{padding:4.5rem 0}
.kicker{display:inline-block;font-size:.78rem;font-weight:700;letter-spacing:.14em;
  text-transform:uppercase;color:var(--accent);margin-bottom:.7rem}
section h2{font-size:clamp(1.5rem,3vw,2rem);letter-spacing:-.02em;margin-bottom:.5rem}
.section-sub{color:var(--muted);max-width:44rem;margin-bottom:2rem}

/* ── header ── */
header.site{position:sticky;top:0;z-index:60;
  background:rgba(18,18,20,.82);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border)}
header.site .wrap{display:flex;align-items:center;gap:1rem;height:68px}
.brand{display:flex;align-items:center;gap:.65rem;font-weight:700;font-size:1.02rem;
  letter-spacing:.12em;color:var(--fg)}
.brand:hover{color:var(--fg)}
.brand svg{width:26px;height:26px;display:block}
nav.main{margin-left:auto;display:flex;gap:1.6rem;font-size:.92rem;font-weight:500}
nav.main a{color:var(--muted);position:relative;padding:.2rem 0}
nav.main a::after{content:"";position:absolute;left:0;right:100%;bottom:-2px;height:2px;
  background:var(--accent);transition:right .22s var(--ease)}
nav.main a:hover{color:var(--fg)}
nav.main a:hover::after,nav.main a.active::after{right:0}
nav.main a.active{color:var(--fg)}
.nav-toggle{display:none;margin-left:auto;background:none;border:1px solid var(--border);
  border-radius:8px;color:var(--fg);padding:.4rem .6rem;font-size:1.05rem;cursor:pointer}
@media(max-width:760px){
  .nav-toggle{display:block}
  nav.main{display:none;position:absolute;top:68px;left:0;right:0;flex-direction:column;
    gap:0;background:var(--bg2);border-bottom:1px solid var(--border);padding:.4rem 0}
  nav.main.open{display:flex}
  nav.main a{padding:.8rem 1.4rem}
  nav.main a::after{display:none}
}

/* ── hero ── */
.hero{padding:5.5rem 0 5rem;border-bottom:1px solid var(--border);
  background:
    radial-gradient(52rem 26rem at 18% -10%,rgba(39,75,143,.28),transparent 60%),
    radial-gradient(40rem 22rem at 92% 8%,rgba(110,168,255,.10),transparent 55%)}
.hero .wrap{display:grid;grid-template-columns:1.5fr .9fr;gap:3rem;align-items:center}
@media(max-width:860px){.hero .wrap{grid-template-columns:1fr}.hero-avatar{order:-1;justify-self:start}}
.hero h1{font-size:clamp(1.9rem,4.6vw,3.1rem);line-height:1.12;letter-spacing:-.03em;
  margin:0 0 1.1rem}
.hero h1 .grad{background:linear-gradient(100deg,var(--accent2),var(--accent) 45%,#4d7fd6);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.hero p.sub{color:var(--muted);font-size:1.12rem;max-width:38rem;margin-bottom:1.9rem}
.cta{display:flex;gap:.9rem;flex-wrap:wrap}
.btn{display:inline-block;font-weight:600;font-size:.98rem;padding:.78rem 1.55rem;
  border-radius:10px;border:1px solid transparent;cursor:pointer;
  transition:transform .18s var(--ease),box-shadow .18s var(--ease),background .18s}
.btn.primary{background:linear-gradient(135deg,var(--navy2),var(--navy));color:#fff;
  box-shadow:0 4px 18px rgba(29,58,110,.45)}
.btn.primary:hover{transform:translateY(-2px);box-shadow:0 8px 26px rgba(39,75,143,.55);color:#fff}
.btn.ghost{background:transparent;color:var(--accent);border-color:var(--border2)}
.btn.ghost:hover{transform:translateY(-2px);border-color:var(--accent);color:var(--accent2)}
.hero-avatar{position:relative;width:min(260px,60vw);aspect-ratio:1}
.hero-avatar .ring{position:absolute;inset:0;border-radius:28px;padding:2px;
  background:linear-gradient(140deg,var(--accent),transparent 40%,var(--navy2) 80%)}
.hero-avatar .ph{position:absolute;inset:2px;border-radius:26px;background:var(--card2);
  display:flex;align-items:center;justify-content:center;flex-direction:column;gap:.4rem;
  border:1px solid var(--border);overflow:hidden}
.hero-avatar .ph span{font-family:"Outfit";font-size:3.2rem;font-weight:700;
  letter-spacing:.06em;color:var(--accent)}
.hero-avatar .ph small{color:var(--faint);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase}
.hero-stats{display:flex;gap:2.2rem;margin-top:2.4rem;flex-wrap:wrap}
.hero-stats b{display:block;font-family:"Outfit";font-size:1.5rem;color:var(--fg)}
.hero-stats span{color:var(--faint);font-size:.85rem}

/* ── tabs (expertise) ── */
.tabs{display:flex;gap:.5rem;flex-wrap:wrap;border-bottom:1px solid var(--border);margin-bottom:1.8rem}
.tab-btn{background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);
  font:inherit;font-weight:600;font-size:.95rem;padding:.7rem 1rem;cursor:pointer;
  transition:color .18s}
.tab-btn:hover{color:var(--fg)}
.tab-btn[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent)}
.tab-panel{display:none}
.tab-panel.active{display:grid;gap:1.4rem;grid-template-columns:1.2fr .8fr;align-items:start;
  animation:fadeUp .35s var(--ease)}
@media(max-width:820px){.tab-panel.active{grid-template-columns:1fr}}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.tab-panel h3{font-size:1.25rem;margin-bottom:.7rem}
.tab-panel p{color:var(--muted);margin-bottom:1rem}
.chiplist{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.4rem}
.chip{font-size:.8rem;font-weight:600;color:var(--accent2);background:rgba(110,168,255,.08);
  border:1px solid rgba(110,168,255,.25);border-radius:999px;padding:.22rem .75rem}
.facts{display:grid;gap:.9rem}
.fact{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:1rem 1.15rem;transition:transform .18s var(--ease),border-color .18s}
.fact:hover{transform:translateY(-3px);border-color:var(--border2)}
.fact b{display:block;font-size:.95rem;margin-bottom:.15rem}
.fact span{color:var(--muted);font-size:.88rem}

/* ── code vault ── */
.pills{display:flex;gap:.55rem;flex-wrap:wrap;margin-bottom:1.8rem}
.pill{background:var(--card);border:1px solid var(--border);border-radius:999px;
  color:var(--muted);font:inherit;font-size:.86rem;font-weight:600;padding:.42rem 1.05rem;
  cursor:pointer;transition:all .18s var(--ease)}
.pill:hover{color:var(--fg);border-color:var(--border2)}
.pill[aria-pressed="true"]{background:rgba(39,75,143,.35);border-color:var(--navy2);color:var(--accent2)}
.vault-grid{display:grid;gap:1.4rem;grid-template-columns:repeat(auto-fit,minmax(min(480px,100%),1fr))}
.codecard{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;box-shadow:var(--shadow);transition:transform .18s var(--ease),border-color .18s}
.codecard:hover{transform:translateY(-3px);border-color:var(--border2)}
.codecard.hidden,.disc-card.hidden{display:none}
.codehead{display:flex;align-items:center;gap:.7rem;padding:.7rem 1rem;
  background:var(--card2);border-bottom:1px solid var(--border)}
.codehead .fname{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:.85rem;color:var(--fg)}
.codehead .lang{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--faint);border:1px solid var(--border2);border-radius:5px;padding:.08rem .5rem}
.copybtn{margin-left:auto;background:none;border:1px solid var(--border2);border-radius:7px;
  color:var(--muted);font:inherit;font-size:.8rem;font-weight:600;padding:.28rem .8rem;
  cursor:pointer;transition:all .15s}
.copybtn:hover{color:var(--fg);border-color:var(--accent)}
.copybtn.done{color:var(--green);border-color:var(--green)}
.codecard pre{padding:1.05rem 1.15rem;overflow-x:auto;max-height:420px;font-size:.83rem;line-height:1.6;
  font-family:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;color:#c8ccd8}
.tok-k{color:var(--tok-k)} .tok-s{color:var(--tok-s)} .tok-c{color:var(--tok-c);font-style:italic}
.tok-n{color:var(--tok-n)} .tok-f{color:var(--tok-f)}

/* ── discussions ── */
.disc-grid{display:grid;gap:1.3rem;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.disc-card{display:flex;flex-direction:column;gap:.6rem;background:var(--card);
  border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem 1.3rem;
  box-shadow:var(--shadow);transition:transform .18s var(--ease),border-color .18s}
.disc-card:hover{transform:translateY(-3px);border-color:var(--border2)}
.disc-cat{align-self:flex-start;font-size:.72rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;border-radius:5px;padding:.14rem .55rem}
.disc-cat.tech{color:var(--accent2);background:rgba(110,168,255,.1)}
.disc-cat.finance{color:var(--green);background:rgba(125,211,160,.1)}
.disc-cat.fitness{color:var(--orange);background:rgba(232,178,109,.1)}
.disc-card h3{font-size:1.06rem;line-height:1.4}
.disc-card p{color:var(--muted);font-size:.9rem;flex:1}
.disc-meta{display:flex;gap:.8rem;color:var(--faint);font-size:.78rem}
.disc-soon{color:var(--orange);font-size:.75rem;font-weight:600}

/* ── contact ── */
.contact-grid{display:grid;gap:2.5rem;grid-template-columns:.8fr 1.2fr}
@media(max-width:820px){.contact-grid{grid-template-columns:1fr}}
form.contact{display:grid;gap:1rem}
form.contact label{display:grid;gap:.35rem;font-weight:600;font-size:.88rem;color:var(--muted)}
form.contact input,form.contact select,form.contact textarea{
  font:inherit;padding:.68rem .85rem;border:1px solid var(--border);border-radius:9px;
  background:var(--bg2);color:var(--fg);width:100%;transition:border-color .15s}
form.contact input:focus,form.contact select:focus,form.contact textarea:focus{
  outline:none;border-color:var(--accent)}
form.contact textarea{min-height:9rem;resize:vertical}
form.contact .row2{display:grid;gap:1rem;grid-template-columns:1fr 1fr}
@media(max-width:600px){form.contact .row2{grid-template-columns:1fr}}
.hp-field{position:absolute!important;left:-9999px!important;width:1px;height:1px;overflow:hidden}
.form-msg{display:none;padding:.7rem .9rem;border-radius:8px;font-size:.92rem}
.form-msg.show{display:block}
.form-msg.ok{background:rgba(125,211,160,.12);color:var(--green)}
.form-msg.err{background:rgba(242,139,130,.12);color:var(--red)}

/* ── pay page ── */
.pay-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}
.pay-card{display:flex;gap:.9rem;align-items:flex-start;background:var(--card);
  border:1px solid var(--border);border-radius:var(--radius);padding:1.1rem 1.2rem;
  box-shadow:var(--shadow);color:var(--fg);transition:transform .18s var(--ease),border-color .18s}
a.pay-card:hover{transform:translateY(-3px);border-color:var(--accent)}
.pay-badge{flex:0 0 44px;height:44px;border-radius:10px;display:flex;align-items:center;
  justify-content:center;font-weight:800;font-size:1.3rem;color:#fff}
.pay-card h3{font-size:1.02rem;margin-bottom:.15rem}
.pay-card p{color:var(--muted);font-size:.88rem;line-height:1.45}
.pay-pending{display:inline-block;margin-top:.3rem;font-size:.75rem;font-weight:700;
  letter-spacing:.03em;color:var(--orange);background:rgba(232,178,109,.12);
  border-radius:5px;padding:.1rem .45rem}

/* ── footer / misc ── */
footer.site{border-top:1px solid var(--border);padding:2.2rem 0;color:var(--faint);font-size:.88rem}
footer.site .wrap{display:flex;gap:1rem;flex-wrap:wrap;justify-content:space-between}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .5s var(--ease),transform .5s var(--ease)}
.reveal.in{opacity:1;transform:none}
@media(prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important}
  html{scroll-behavior:auto}
  .reveal{opacity:1;transform:none}
}
"""

JS = """
(function () {
  "use strict";

  // ── mobile nav ──────────────────────────────────────────────────────────
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector("nav.main");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (ev) {
      if (ev.target.tagName === "A") nav.classList.remove("open");
    });
  }

  // ── expertise tabs ──────────────────────────────────────────────────────
  var tabBtns = document.querySelectorAll(".tab-btn");
  function selectTab(id) {
    tabBtns.forEach(function (b) {
      b.setAttribute("aria-selected", b.dataset.tab === id ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach(function (p) {
      p.classList.toggle("active", p.id === "panel-" + id);
    });
  }
  tabBtns.forEach(function (b) {
    b.addEventListener("click", function () { selectTab(b.dataset.tab); });
  });

  // ── filter pills (code vault + discussions) ─────────────────────────────
  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var pills = group.querySelectorAll(".pill");
    var items = document.querySelectorAll(group.dataset.filterGroup);
    pills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        pills.forEach(function (p) { p.setAttribute("aria-pressed", "false"); });
        pill.setAttribute("aria-pressed", "true");
        var want = pill.dataset.cat;
        items.forEach(function (it) {
          it.classList.toggle("hidden", want !== "all" && it.dataset.cat !== want);
        });
      });
    });
  });

  // ── copy buttons ────────────────────────────────────────────────────────
  document.querySelectorAll(".copybtn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var pre = btn.closest(".codecard").querySelector("pre");
      // textContent strips the syntax-highlight spans — raw code only.
      navigator.clipboard.writeText(pre.textContent).then(function () {
        var old = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("done");
        setTimeout(function () {
          btn.textContent = old;
          btn.classList.remove("done");
        }, 1600);
      }, function () {
        btn.textContent = "Press Ctrl+C";
      });
    });
  });

  // ── scroll reveal + active nav link ─────────────────────────────────────
  if ("IntersectionObserver" in window) {
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (el) { ro.observe(el); });

    var links = document.querySelectorAll("nav.main a[href^='#'], nav.main a[href^='/#']");
    var map = {};
    links.forEach(function (l) {
      var id = l.getAttribute("href").split("#")[1];
      if (id) map[id] = l;
    });
    var so = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var link = map[e.target.id];
        if (link && e.isIntersecting) {
          links.forEach(function (l) { l.classList.remove("active"); });
          link.classList.add("active");
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(map).forEach(function (id) {
      var sec = document.getElementById(id);
      if (sec) so.observe(sec);
    });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  // ── contact form → POST /api/contact ────────────────────────────────────
  function show(msg, ok, text) {
    msg.textContent = text;
    msg.className = "form-msg show " + (ok ? "ok" : "err");
  }
  document.querySelectorAll("form[data-contact]").forEach(function (form) {
    var msg = form.querySelector(".form-msg");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var payload = {
        name: form.elements["name"].value.trim(),
        email: form.elements["email"].value.trim(),
        company: form.elements["company"].value.trim(),
        topic: form.elements["topic"].value,
        message: form.elements["message"].value.trim(),
        website: form.elements["website"].value
      };
      if (!payload.name || !payload.email || !payload.message) {
        show(msg, false, "Please fill in your name, email, and message.");
        return;
      }
      btn.disabled = true;
      fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (r.ok && d && d.ok) {
            form.reset();
            show(msg, true, "Thanks — your message has been sent.");
          } else {
            show(msg, false, (d && d.error) ||
              "Something went wrong. Please email derek@derekcoleman.com instead.");
          }
        });
      }).catch(function () {
        show(msg, false, "Network error — please try again, or email derek@derekcoleman.com.");
      }).finally(function () {
        btn.disabled = false;
      });
    });
  });
})();
"""

# ─── tiny syntax highlighter (build-time, no runtime JS cost) ────────────────

_LANG_PATTERNS = {
    "python": re.compile(
        r'(?P<c>#[^\n]*)'
        r'|(?P<s>"""[\s\S]*?"""|\'[^\'\n]*\'|"[^"\n]*")'
        r'|(?P<k>\b(?:from|import|def|class|return|if|elif|else|for|while|in|not'
        r'|or|and|async|await|raise|try|except|finally|with|as|lambda|pass'
        r'|None|True|False|yield)\b)'
        r'|(?P<f>\b\w+(?=\())'
        r'|(?P<n>\b\d+(?:\.\d+)?\b)'),
    "yaml": re.compile(
        r'(?P<c>#[^\n]*)'
        r"|(?P<s>'[^'\n]*'|\"[^\"\n]*\")"
        r'|(?P<k>^[ \t]*-?[ \t]*[\w./_-]+(?=:))'
        r'|(?P<n>\b\d+(?:\.\d+)?(?:e-?\d+)?\b)', re.MULTILINE),
    "hcl": re.compile(
        r'(?P<c>#[^\n]*)'
        r'|(?P<s>"[^"\n]*")'
        r'|(?P<k>\b(?:module|resource|variable|output|provider|locals|data'
        r'|source|true|false|for_each|depends_on|type|default)\b)'
        r'|(?P<n>\b\d+(?:\.\d+)?\b)'),
    "ini": re.compile(
        r'(?P<c>^[;#][^\n]*)'
        r'|(?P<k>^\[[^\]\n]+\]|^[A-Za-z][\w-]*(?==))'
        r'|(?P<n>\b\d+\b)', re.MULTILINE),
}

_TOK_CLASS = {"c": "tok-c", "s": "tok-s", "k": "tok-k", "n": "tok-n", "f": "tok-f"}


def hl(code: str, lang: str) -> str:
    """Wrap tokens in span.tok-* classes; HTML-escapes everything."""
    pat = _LANG_PATTERNS.get(lang)
    if pat is None:
        return esc(code)
    out, pos = [], 0
    for m in pat.finditer(code):
        out.append(esc(code[pos:m.start()]))
        cls = _TOK_CLASS[m.lastgroup]
        out.append(f'<span class="{cls}">{esc(m.group())}</span>')
        pos = m.end()
    out.append(esc(code[pos:]))
    return "".join(out)


# ─── code vault samples ───────────────────────────────────────────────────────

CODE_SAMPLES = [
    {
        "fname": "model_router.py", "lang": "python", "label": "Python", "cat": "python",
        "code": '''# model_router.py — FastAPI gateway routing chat completions across
# private inference pools. Nothing leaves the boundary: every upstream is
# an internal vLLM endpoint or a private-link cloud pool.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

UPSTREAMS = {
    "fast":  "http://vllm-l40s.internal:8000/v1",   # Llama-3-8B, low latency
    "smart": "http://vllm-h100.internal:8000/v1",   # Llama-3-70B, hard questions
    "batch": "https://gpu-pool.oci.internal/v1",    # OCI pool via private link
}
ROUTE_BY_BUDGET_MS = [(350, "fast"), (2500, "smart")]

app = FastAPI(title="model-router")

class ChatReq(BaseModel):
    messages: list[dict]
    model: str = "auto"
    latency_budget_ms: int = 2500
    max_tokens: int = 512

def pick(req: ChatReq) -> str:
    if req.model != "auto":
        if req.model not in UPSTREAMS:
            raise HTTPException(400, f"unknown model tier {req.model!r}")
        return UPSTREAMS[req.model]
    for budget, tier in ROUTE_BY_BUDGET_MS:
        if req.latency_budget_ms <= budget:
            return UPSTREAMS[tier]
    return UPSTREAMS["batch"]

@app.post("/v1/chat/completions")
async def route(req: ChatReq):
    upstream = pick(req)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{upstream}/chat/completions",
                              json=req.model_dump(exclude={"latency_budget_ms"}))
        r.raise_for_status()
        return r.json()
''',
    },
    {
        "fname": "llama3-qlora.yaml", "lang": "yaml", "label": "Axolotl", "cat": "configs",
        "code": '''# llama3-qlora.yaml — Axolotl QLoRA fine-tune that fits one 24 GB GPU.
# Train on your own transcripts; weights never leave the building.
base_model: meta-llama/Meta-Llama-3-8B-Instruct
load_in_4bit: true
adapter: qlora

lora_r: 32
lora_alpha: 16
lora_dropout: 0.05
lora_target_modules: [q_proj, k_proj, v_proj, o_proj]

datasets:
  - path: data/support-transcripts.jsonl
    type: chat_template

sequence_len: 4096
sample_packing: true
micro_batch_size: 2
gradient_accumulation_steps: 8
num_epochs: 3
learning_rate: 2e-4
lr_scheduler: cosine
warmup_ratio: 0.05
bf16: auto
gradient_checkpointing: true

output_dir: ./outputs/llama3-support-lora
''',
    },
    {
        "fname": "data_plane.tf", "lang": "hcl", "label": "Terraform", "cat": "terraform",
        "code": '''# data_plane.tf — zero-trust split: the control plane orchestrates,
# but customer data never leaves the customer\\'s private VPC boundary.
module "customer_data_plane" {
  source   = "./modules/data-plane"
  for_each = var.customers

  vpc_cidr             = each.value.cidr
  allow_public_ingress = false            # no exceptions
  db_subnet_tier       = "isolated"       # no route to an IGW/NAT

  # Control plane reaches in via PrivateLink only — never the reverse.
  control_plane_endpoint_service = aws_vpc_endpoint_service.control.id
}

resource "aws_security_group_rule" "db_ingress" {
  for_each          = var.customers
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  security_group_id = module.customer_data_plane[each.key].db_sg_id
  # Only the customer\\'s own app tier — no 0.0.0.0/0, ever.
  source_security_group_id = module.customer_data_plane[each.key].app_sg_id
}
''',
    },
    {
        "fname": "vllm.service", "lang": "ini", "label": "systemd", "cat": "configs",
        "code": '''# vllm.service — production inference serving, OpenAI-compatible API.
# High throughput via continuous batching + tensor parallelism.
[Unit]
Description=vLLM inference server (Llama-3-70B-Instruct)
After=network-online.target

[Service]
User=vllm
Restart=always
RestartSec=5
Environment=HF_HUB_OFFLINE=1
ExecStart=/opt/vllm/bin/vllm serve meta-llama/Meta-Llama-3-70B-Instruct \\
  --host 127.0.0.1 --port 8000 \\
  --tensor-parallel-size 4 \\
  --max-model-len 8192 \\
  --gpu-memory-utilization 0.92 \\
  --api-key-file /etc/vllm/api-keys

[Install]
WantedBy=multi-user.target
''',
    },
]

# ─── discussions feed ────────────────────────────────────────────────────────
# Placeholder editorial calendar — cards render as drafts until real posts exist.

DISCUSSIONS = [
    {"cat": "tech", "title": "Running Llama-3 Behind Your Own Firewall: a vLLM Production Checklist",
     "excerpt": "GPU memory headroom, continuous batching, API-key rotation, and the monitoring you need before an internal LLM endpoint counts as production.",
     "date": "July 2026", "read": "9 min"},
    {"cat": "tech", "title": "The API Proxy Gateway Pattern for LLM Traffic",
     "excerpt": "Put one gateway between every app and every model — routing, budget caps, PII scrubbing, and audit logs in a single choke point.",
     "date": "July 2026", "read": "7 min"},
    {"cat": "tech", "title": "Avoiding the Vulnerability De-listing Trap in Cloud Marketplaces",
     "excerpt": "Why a marketplace image that passed certification last month can be de-listed today, and the CVE-freshening pipeline that prevents it.",
     "date": "June 2026", "read": "8 min"},
    {"cat": "finance", "title": "SaaS Pricing Models for Infrastructure Software",
     "excerpt": "Per-vCPU, per-node, flat-tier: what actually clears procurement in enterprise accounts, with real marketplace data.",
     "date": "July 2026", "read": "6 min"},
    {"cat": "finance", "title": "Burning Down Committed Cloud Spend Without Wasting It",
     "excerpt": "Committed-spend agreements expire whether you use them or not. A framework for routing real workloads at the burn-down.",
     "date": "June 2026", "read": "7 min"},
    {"cat": "finance", "title": "Strategic Planning for a Family-Owned Technology Business",
     "excerpt": "Annual planning that survives contact with reality: capital allocation, partner programs, and when to say no to growth.",
     "date": "May 2026", "read": "10 min"},
    {"cat": "fitness", "title": "Training Consistency When You Run a Company",
     "excerpt": "The minimum-effective-dose program that survives travel weeks, launch weeks, and everything in between.",
     "date": "July 2026", "read": "5 min"},
    {"cat": "fitness", "title": "A Diet Plan You Can Actually Sustain at a Desk",
     "excerpt": "Protein targets, meal timing around deep-work blocks, and what to keep out of the office entirely.",
     "date": "June 2026", "read": "6 min"},
]

# ─── page chrome ──────────────────────────────────────────────────────────────

LOGO_SVG = """<svg viewBox="0 0 32 32" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<g transform="rotate(45 16 16)">
<rect x="5" y="5" width="10" height="10" rx="2" fill="#274b8f"/>
<rect x="17" y="5" width="10" height="10" rx="2" fill="#6ea8ff"/>
<rect x="5" y="17" width="10" height="10" rx="2" fill="#6ea8ff"/>
<rect x="17" y="17" width="10" height="10" rx="2" fill="#1d3a6e"/>
</g></svg>"""

FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap">"""


def header(depth: int) -> str:
    r = "../" * depth
    home = r if depth else "./"
    return f"""<header class="site"><div class="wrap">
  <a class="brand" href="{home}">{LOGO_SVG}DEREK&nbsp;COLEMAN</a>
  <button class="nav-toggle" aria-label="Menu" aria-expanded="false">☰</button>
  <nav class="main">
    <a href="{r}#top">Home</a>
    <a href="{r}#expertise">Expertise</a>
    <a href="{r}#vault">Code Vault</a>
    <a href="{r}#discussions">Discussions</a>
    <a href="{r}#contact">Contact</a>
  </nav>
</div></header>"""


def footer() -> str:
    return f"""<footer class="site"><div class="wrap">
  <span>© {datetime.date.today().year} Derek Coleman · CEO, Derek Coleman &amp; Associates Group</span>
  <span>
    <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> ·
    <a href="{LINKEDIN}" rel="noopener">LinkedIn</a> ·
    <a href="{GITHUB_ORG}" rel="noopener">GitHub</a> ·
    <a href="/pay/">Pay</a> ·
    <a href="{COMPANY_SITE}" rel="noopener">DC Associates Group</a>
  </span>
</div></footer>"""


def page(*, title: str, description: str, body: str, depth: int, path: str | None,
         noindex: bool = False) -> str:
    r = "../" * depth
    canonical = f"{SITE}/{path}" if path is not None else ""
    seo = ""
    if canonical:
        seo += f'<link rel="canonical" href="{esc(canonical)}">\n'
    if noindex:
        seo += '<meta name="robots" content="noindex">\n'
    seo += f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="Derek Coleman">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#121214">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{seo}
{FONTS}
<link rel="stylesheet" href="{r}assets/site.css">
</head>
<body id="top">
{header(depth)}
<main>
{body}
</main>
{footer()}
<script src="{r}assets/app.js" defer></script>
</body>
</html>
"""


def write(path: str, content: str) -> None:
    out = PUB / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    if path.endswith("index.html"):
        SITEMAP_PATHS.append(path[: -len("index.html")])


# ─── sections ─────────────────────────────────────────────────────────────────

def hero_section() -> str:
    return f"""<div class="hero"><div class="wrap">
  <div>
    <h1>Distinguished Architect. CEO.<br>
      <span class="grad">Securing Local Generative AI</span> for Production.</h1>
    <p class="sub">Developing private, secure language models and high-performance
      multi-cloud architectures for enterprise environments.</p>
    <div class="cta">
      <a class="btn primary" href="#expertise">Explore My Work</a>
      <a class="btn ghost" href="#discussions">Read Discussions</a>
    </div>
    <div class="hero-stats">
      <div><b>100+</b><span>live marketplace offers</span></div>
      <div><b>4 clouds</b><span>Azure · AWS · OCI · GCP</span></div>
      <div><b>Local-first</b><span>LLMs inside the boundary</span></div>
    </div>
  </div>
  <div class="hero-avatar">
    <div class="ring"></div>
    <!-- TODO(operator): replace the placeholder below with the LinkedIn profile
         photo, e.g. <img src="../assets/derek.jpg" alt="Derek Coleman"
         style="width:100%;height:100%;object-fit:cover"> inside .ph -->
    <div class="ph"><span>DC</span><small>photo pending</small></div>
  </div>
</div></div>"""


def expertise_section() -> str:
    panels = {
        "ai": {
            "btn": "AI &amp; Language Models",
            "h": "Private, production-grade language models",
            "p": ("Open-source models — OLMo, Llama-3 — deployed as local production "
                  "systems inside the security boundary, for environments where prompts "
                  "and weights can never leave the building. Custom fine-tuning pipelines "
                  "built on Axolotl with LoRA/QLoRA adapters, served at high throughput "
                  "with vLLM continuous batching."),
            "chips": ["OLMo", "Llama-3", "Axolotl", "LoRA / QLoRA", "vLLM", "Private inference"],
            "facts": [
                ("Fine-tuning pipelines", "Reproducible Axolotl configs from raw transcripts to evaluated adapters."),
                ("Inference serving", "vLLM with tensor parallelism, token budgets, and per-app API keys."),
                ("Security posture", "Air-gap-friendly: offline HuggingFace hub, no telemetry, audited egress."),
            ],
        },
        "arch": {
            "btn": "Enterprise Architecture",
            "h": "Zero-trust multi-cloud, control/data plane split",
            "p": ("Architectures spanning AWS, Azure, GCP, and Oracle Cloud Infrastructure "
                  "(OCI) built on a strict control plane / data plane separation: the "
                  "vendor's control plane orchestrates, while customer databases stay "
                  "inside the customer's own private VPC boundary — reached only via "
                  "private endpoints, never the public internet."),
            "chips": ["AWS", "Azure", "GCP", "OCI", "Zero trust", "PrivateLink", "IaC"],
            "facts": [
                ("Data sovereignty", "Customer data planes with no public ingress and no route out."),
                ("Marketplace scale", "100+ certified offers with CI-gated compliance pipelines."),
                ("Image factories", "Packer + CIS-hardened builds, CVE freshening on a treadmill."),
            ],
        },
        "exec": {
            "btn": "Executive Leadership",
            "h": "CEO &amp; business owner",
            "p": ("Founder and CEO of Derek Coleman &amp; Associates Group, managing "
                  "family-business operations end to end — strategy, finance, and "
                  "delivery — while driving multi-cloud go-to-market co-selling "
                  "partnerships across the Microsoft, AWS, Oracle, and Google "
                  "partner ecosystems."),
            "chips": ["P&amp;L ownership", "GTM strategy", "Co-sell programs", "Partner ecosystems"],
            "facts": [
                ("Co-sell coverage", "40+ solutions co-sell ready across partner programs."),
                ("Operating cadence", "Owner-operator discipline: strategy through execution."),
                ("2027 targets", "A programmatic path to hundreds of monetized offers."),
            ],
        },
    }
    btns, bodies = [], []
    for i, (key, p) in enumerate(panels.items()):
        sel = "true" if i == 0 else "false"
        btns.append(f'<button class="tab-btn" role="tab" data-tab="{key}" aria-selected="{sel}">{p["btn"]}</button>')
        chips = "".join(f'<span class="chip">{c}</span>' for c in p["chips"])
        facts = "".join(f'<div class="fact"><b>{esc(t)}</b><span>{esc(s)}</span></div>'
                        for t, s in p["facts"])
        bodies.append(f"""<div class="tab-panel{' active' if i == 0 else ''}" id="panel-{key}" role="tabpanel">
  <div><h3>{p["h"]}</h3><p>{p["p"]}</p><div class="chiplist">{chips}</div></div>
  <div class="facts">{facts}</div>
</div>""")
    return f"""<section id="expertise"><div class="wrap reveal">
  <span class="kicker">Expertise</span>
  <h2>Three disciplines, one operator</h2>
  <p class="section-sub">Toggle between the core areas of my work.</p>
  <div class="tabs" role="tablist">{"".join(btns)}</div>
  {"".join(bodies)}
</div></section>"""


def vault_section() -> str:
    cats = [("all", "All"), ("python", "Python"), ("terraform", "Terraform"), ("configs", "Configs")]
    pills = "".join(
        f'<button class="pill" data-cat="{c}" aria-pressed="{"true" if c == "all" else "false"}">{l}</button>'
        for c, l in cats)
    cards = []
    for s in CODE_SAMPLES:
        cards.append(f"""<div class="codecard" data-cat="{s["cat"]}">
  <div class="codehead">
    <span class="fname">{esc(s["fname"])}</span>
    <span class="lang">{esc(s["label"])}</span>
    <button class="copybtn" type="button">Copy</button>
  </div>
  <pre><code>{hl(s["code"], s["lang"])}</code></pre>
</div>""")
    return f"""<section id="vault"><div class="wrap reveal">
  <span class="kicker">Code Vault</span>
  <h2>Copy-paste playground</h2>
  <p class="section-sub">Working patterns from real deployments — routing gateways,
    fine-tuning templates, zero-trust infrastructure. Copy freely.</p>
  <div class="pills" data-filter-group="#vault .codecard">{pills}</div>
  <div class="vault-grid">{"".join(cards)}</div>
</div></section>"""


def discussions_section() -> str:
    cats = [("all", "All"), ("tech", "Tech"), ("finance", "Finance"), ("fitness", "Fitness")]
    pills = "".join(
        f'<button class="pill" data-cat="{c}" aria-pressed="{"true" if c == "all" else "false"}">{l}</button>'
        for c, l in cats)
    cards = []
    for d in DISCUSSIONS:
        cards.append(f"""<article class="disc-card" data-cat="{d["cat"]}">
  <span class="disc-cat {d["cat"]}">{d["cat"].capitalize()}</span>
  <h3>{esc(d["title"])}</h3>
  <p>{esc(d["excerpt"])}</p>
  <div class="disc-meta"><span>{esc(d["date"])}</span><span>{esc(d["read"])} read</span>
    <span class="disc-soon">Draft — full post coming soon</span></div>
</article>""")
    return f"""<section id="discussions" style="background:var(--bg2)"><div class="wrap reveal">
  <span class="kicker">Discussions</span>
  <h2>Notes from the field</h2>
  <p class="section-sub">Technology, finance, and fitness — the three feeds I actually write.</p>
  <div class="pills" data-filter-group="#discussions .disc-card">{pills}</div>
  <div class="disc-grid">{"".join(cards)}</div>
</div></section>"""


CONTACT_TOPICS = ["General", "Consulting", "Speaking", "Other"]


def contact_section() -> str:
    topics = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in CONTACT_TOPICS)
    return f"""<section id="contact"><div class="wrap reveal">
  <div class="contact-grid">
    <div>
      <span class="kicker">Contact</span>
      <h2>Let's talk</h2>
      <p class="section-sub">Consulting, partnerships, speaking — or just compare notes
        on running language models where the data already lives.
        Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> or use the form.</p>
    </div>
    <form class="contact" id="contact-form" data-contact novalidate>
      <div class="row2">
        <label>Name<input type="text" name="name" autocomplete="name" maxlength="200" required></label>
        <label>Email<input type="email" name="email" autocomplete="email" maxlength="320" required></label>
      </div>
      <div class="row2">
        <label>Company (optional)<input type="text" name="company" autocomplete="organization" maxlength="300"></label>
        <label>Topic<select name="topic" required>{topics}</select></label>
      </div>
      <label>Message<textarea name="message" maxlength="5000" required></textarea></label>
      <div class="hp-field" aria-hidden="true">
        <label>Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label>
      </div>
      <p class="form-msg" role="status" aria-live="polite"></p>
      <button class="btn primary" type="submit">Send message</button>
    </form>
  </div>
</div></section>"""


def home() -> str:
    body = hero_section() + expertise_section() + vault_section() \
        + discussions_section() + contact_section()
    return page(
        title="Derek Coleman — Distinguished Architect · CEO · AI Innovator",
        description="Derek Coleman: securing local generative AI for production. Private "
                    "language models, zero-trust multi-cloud architecture, and executive "
                    "leadership across Azure, AWS, OCI, and GCP.",
        body=body, depth=0, path="")


def pay_page() -> str:
    cards = []
    for p in PAYMENTS:
        badge = f'<span class="pay-badge" style="background:{p["color"]}">{esc(p["abbr"] or p["name"][0])}</span>'
        inner = f"""{badge}
  <span><h3>{esc(p["name"])}</h3>
  <p>{esc(p["note"])}</p>
  {'' if p["handle"] else '<span class="pay-pending">HANDLE PENDING — placeholder</span>'}</span>"""
        if p["url"] and p["handle"]:
            cards.append(f'<a class="pay-card" href="{esc(p["url"])}" rel="noopener">{inner}</a>')
        else:
            cards.append(f'<div class="pay-card">{inner}</div>')
    body = f"""<section><div class="wrap">
  <span class="kicker">Payments</span>
  <h2>Pay Derek</h2>
  <p class="section-sub">Payment and fintech apps I accept. If a method you need isn't
    listed, <a href="../#contact">get in touch</a>.</p>
  <div class="pay-grid">{"".join(cards)}</div>
</div></section>"""
    return page(title="Pay — Derek Coleman",
                description="Payment methods accepted by Derek Coleman: Cash App, Venmo, PayPal, Zelle, and more.",
                body=body, depth=1, path="pay/")


def not_found() -> str:
    body = """<section><div class="wrap">
  <h2>Page not found</h2>
  <p class="section-sub">That page doesn't exist. <a href="/">Back to the home page.</a></p>
</div></section>"""
    return page(title="404 — Derek Coleman", description="Page not found.",
                body=body, depth=0, path=None, noindex=True)


SWA_CONFIG = {
    "trailingSlash": "auto",
    "platform": {"apiRuntime": "node:20"},
    "routes": [
        {"route": "/pay", "rewrite": "/pay/index.html"},
        {"route": "/contact", "redirect": "/#contact", "statusCode": 302},
    ],
    "responseOverrides": {
        "404": {"rewrite": "/404.html", "statusCode": 404},
    },
    "globalHeaders": {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    },
    "mimeTypes": {".json": "application/json", ".xml": "application/xml"},
}


def sitemap() -> str:
    urls = "".join(
        f"  <url><loc>{SITE}/{esc(p)}</loc></url>\n" for p in sorted(SITEMAP_PATHS)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def main() -> None:
    if PUB.exists():
        shutil.rmtree(PUB)
    PUB.mkdir(parents=True)

    write("index.html", home())
    write("pay/index.html", pay_page())
    write("404.html", not_found())
    write("assets/site.css", CSS)
    write("assets/app.js", JS)
    write("staticwebapp.config.json", json.dumps(SWA_CONFIG, indent=2) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    write("sitemap.xml", sitemap())

    print(f"built {sum(1 for _ in PUB.rglob('*') if _.is_file())} files → {PUB}")


if __name__ == "__main__":
    main()
