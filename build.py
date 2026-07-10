#!/usr/bin/env python3
"""build.py — static site generator for derekcoleman.com.

Personal landing site. Trimmed clone of the dcassociatesgroup-website
generator: same architecture (stdlib-only, writes the deployable site to
public/, deployed by GitHub Actions → Azure Static Web Apps), minus the
marketplace catalog machinery.

Usage: python3 build.py
"""
from __future__ import annotations

import datetime
import html
import json
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

# ─── shared page chrome ───────────────────────────────────────────────────────

CSS = """
:root{
  --green:#009a49; --teal:#007377; --blue:#0b50a4;
  --bg:#ffffff; --bg2:#f4f7f9; --fg:#16232e; --muted:#5b6b78;
  --card:#ffffff; --border:#dde5ea; --accent:var(--blue); --accent-fg:#ffffff;
  --hero-grad:linear-gradient(135deg,#e8f5ee 0%,#e3f0f1 50%,#e6eef8 100%);
  --shadow:0 1px 3px rgba(22,35,46,.08),0 8px 24px rgba(22,35,46,.06);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0e1419; --bg2:#131b22; --fg:#e7edf2; --muted:#93a4b1;
    --card:#17212a; --border:#243240; --accent:#4d8fd6; --accent-fg:#ffffff;
    --hero-grad:linear-gradient(135deg,#0f2418 0%,#0e2426 50%,#101f33 100%);
    --shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
  }
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font:16px/1.65 "Inter","Segoe UI",-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
img{max-width:100%;height:auto}
.wrap{max-width:880px;margin:0 auto;padding:0 1.25rem}
header.site{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--border)}
header.site .wrap{display:flex;align-items:center;gap:1rem;height:64px}
.brand{font-weight:700;color:var(--fg);letter-spacing:-.01em}
.brand:hover{text-decoration:none}
nav.main{margin-left:auto;display:flex;gap:1.4rem;font-size:.95rem;font-weight:500}
nav.main a{color:var(--fg);opacity:.85}
nav.main a:hover{opacity:1;color:var(--accent);text-decoration:none}
.btn{display:inline-block;background:var(--accent);color:var(--accent-fg)!important;font-weight:600;
  padding:.7rem 1.4rem;border-radius:8px;box-shadow:var(--shadow);border:0;cursor:pointer;font-size:1rem}
.btn:hover{text-decoration:none;filter:brightness(1.08)}
.btn.ghost{background:transparent;color:var(--accent)!important;border:1.5px solid var(--accent);box-shadow:none}
.hero{background:var(--hero-grad);padding:4.5rem 0 4rem;border-bottom:1px solid var(--border)}
.hero h1{font-size:clamp(1.9rem,4.5vw,2.8rem);line-height:1.15;letter-spacing:-.02em;margin-bottom:1rem}
.hero p{max-width:46rem;color:var(--muted);font-size:1.1rem;margin-bottom:1.6rem}
.hero .cta{display:flex;gap:.8rem;flex-wrap:wrap}
section{padding:3rem 0}
section h2{font-size:1.5rem;letter-spacing:-.01em;margin-bottom:1.2rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.2rem 1.3rem;box-shadow:var(--shadow)}
.card h3{font-size:1.05rem;margin-bottom:.4rem}
.card p{color:var(--muted);font-size:.95rem}
footer.site{border-top:1px solid var(--border);padding:2rem 0;color:var(--muted);font-size:.9rem}
footer.site .wrap{display:flex;gap:1rem;flex-wrap:wrap;justify-content:space-between}
form.contact{display:grid;gap:1rem;max-width:40rem}
form.contact label{display:grid;gap:.35rem;font-weight:600;font-size:.92rem}
form.contact input,form.contact select,form.contact textarea{
  font:inherit;padding:.65rem .8rem;border:1px solid var(--border);border-radius:8px;
  background:var(--bg);color:var(--fg);width:100%}
form.contact textarea{min-height:9rem;resize:vertical}
form.contact .row2{display:grid;gap:1rem;grid-template-columns:1fr 1fr}
@media(max-width:600px){form.contact .row2{grid-template-columns:1fr}}
.hp-field{position:absolute!important;left:-9999px!important;width:1px;height:1px;overflow:hidden}
.form-msg{display:none;padding:.7rem .9rem;border-radius:8px;font-size:.95rem}
.form-msg.show{display:block}
.form-msg.ok{background:rgba(0,154,73,.12);color:var(--green)}
.form-msg.err{background:rgba(200,50,50,.1);color:#c03232}
@media (prefers-color-scheme: dark){
  .form-msg.ok{background:rgba(0,154,73,.18);color:#57d38c}
  .form-msg.err{background:rgba(240,90,90,.14);color:#f28b82}}
"""

CONTACT_TOPICS = ["General", "Consulting", "Speaking", "Other"]


def contact_form(form_id: str) -> str:
    """Shared contact form markup; wired to POST /api/contact by assets/contact.js.

    The "website" field is a honeypot: visually hidden, ignored by humans,
    filled by bots — the API silently drops submissions that populate it.
    """
    topics = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in CONTACT_TOPICS)
    return f"""<form class="contact" id="{esc(form_id)}" data-contact novalidate>
  <div class="row2">
    <label>Name<input type="text" name="name" autocomplete="name" maxlength="200" required></label>
    <label>Email<input type="email" name="email" autocomplete="email" maxlength="320" required></label>
  </div>
  <div class="row2">
    <label>Company <span style="font-weight:400;color:var(--muted)">(optional)</span>
      <input type="text" name="company" autocomplete="organization" maxlength="300"></label>
    <label>Topic<select name="topic" required>{topics}</select></label>
  </div>
  <label>Message<textarea name="message" maxlength="5000" required></textarea></label>
  <div class="hp-field" aria-hidden="true">
    <label>Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label>
  </div>
  <p class="form-msg" role="status" aria-live="polite"></p>
  <button class="btn" type="submit">Send message</button>
</form>"""


CONTACT_JS = f"""(function () {{
  "use strict";
  function show(msg, ok, text) {{
    msg.textContent = text;
    msg.className = "form-msg show " + (ok ? "ok" : "err");
  }}
  function init(form) {{
    var msg = form.querySelector(".form-msg");
    form.addEventListener("submit", function (ev) {{
      ev.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var payload = {{
        name: form.elements["name"].value.trim(),
        email: form.elements["email"].value.trim(),
        company: form.elements["company"].value.trim(),
        topic: form.elements["topic"].value,
        message: form.elements["message"].value.trim(),
        website: form.elements["website"].value
      }};
      if (!payload.name || !payload.email || !payload.message) {{
        show(msg, false, "Please fill in your name, email, and message.");
        return;
      }}
      btn.disabled = true;
      fetch("/api/contact", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }}).then(function (r) {{
        return r.json().catch(function () {{ return {{}}; }}).then(function (d) {{
          if (r.ok && d && d.ok) {{
            form.reset();
            show(msg, true, "Thanks — your message has been sent.");
          }} else {{
            show(msg, false, (d && d.error) ||
              "Something went wrong. Please email {CONTACT_EMAIL} instead.");
          }}
        }});
      }}).catch(function () {{
        show(msg, false, "Network error — please try again, or email {CONTACT_EMAIL}.");
      }}).finally(function () {{
        btn.disabled = false;
      }});
    }});
  }}
  var forms = document.querySelectorAll("form[data-contact]");
  for (var i = 0; i < forms.length; i++) init(forms[i]);
}})();
"""


def page(*, title: str, description: str, body: str, depth: int, path: str | None,
         noindex: bool = False) -> str:
    """Render a full page. path — site-relative path with trailing slash
    ("" for home, "contact/", …); None = no canonical (404 page)."""
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
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{seo}
<link rel="stylesheet" href="{r}assets/site.css">
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="{r if depth else './'}">Derek Coleman</a>
  <nav class="main">
    <a href="{r}#work">Work</a>
    <a href="{r}contact/">Contact</a>
    <a href="{COMPANY_SITE}" rel="noopener">DC Associates Group</a>
  </nav>
</div></header>
<main>
{body}
</main>
<footer class="site"><div class="wrap">
  <span>© {datetime.date.today().year} Derek Coleman</span>
  <span>
    <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> ·
    <a href="{LINKEDIN}" rel="noopener">LinkedIn</a> ·
    <a href="{GITHUB_ORG}" rel="noopener">GitHub</a>
  </span>
</div></footer>
<script src="{r}assets/contact.js" defer></script>
</body>
</html>
"""


def write(path: str, content: str) -> None:
    out = PUB / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    if path.endswith("index.html"):
        rel = path[: -len("index.html")]
        SITEMAP_PATHS.append(rel)


# ─── pages ────────────────────────────────────────────────────────────────────

def home() -> str:
    body = f"""<div class="hero"><div class="wrap">
  <h1>Cloud marketplace engineering, done end-to-end.</h1>
  <p>I'm Derek Coleman — founder of Derek Coleman &amp; Associates Group.
     I build and operate commercial software listings across the Azure, AWS,
     Oracle Cloud Infrastructure (OCI), and Google Cloud marketplaces:
     image factories, certification pipelines, and the CI/CD that keeps a
     fleet of offers continuously publishable.</p>
  <div class="cta">
    <a class="btn" href="contact/">Get in touch</a>
    <a class="btn ghost" href="{COMPANY_SITE}" rel="noopener">Visit DC Associates Group</a>
  </div>
</div></div>

<section id="work"><div class="wrap">
  <h2>What I work on</h2>
  <div class="cards">
    <div class="card"><h3>Marketplace publishing</h3>
      <p>100+ live Azure Marketplace offers — virtual machine images, Azure
         Kubernetes Service (AKS) apps, and managed applications — plus
         expansion programs on AWS, OCI, and GCP.</p></div>
    <div class="card"><h3>Image factories</h3>
      <p>Packer-based build pipelines producing hardened, certification-ready
         images with CIS (Center for Internet Security) baselines, CVE
         freshening, and build-time smoke tests.</p></div>
    <div class="card"><h3>Certification automation</h3>
      <p>Machine-checkable certification parameters enforced as CI gates, so
         offers pass marketplace review on the first submission.</p></div>
  </div>
</div></section>
"""
    return page(title="Derek Coleman — cloud marketplace engineering",
                description="Personal site of Derek Coleman: cloud marketplace publishing, "
                            "image factories, and certification automation across Azure, AWS, OCI, and GCP.",
                body=body, depth=0, path="")


def contact_page() -> str:
    body = f"""<section><div class="wrap">
  <h2>Contact</h2>
  <p style="color:var(--muted);margin-bottom:1.4rem">
    Send a note below, or email
    <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> directly.</p>
  {contact_form("contact-form")}
</div></section>
"""
    return page(title="Contact — Derek Coleman",
                description="Get in touch with Derek Coleman.",
                body=body, depth=1, path="contact/")


def not_found() -> str:
    body = """<section><div class="wrap">
  <h2>Page not found</h2>
  <p style="color:var(--muted)">That page doesn't exist. <a href="/">Back to the home page.</a></p>
</div></section>
"""
    return page(title="404 — Derek Coleman", description="Page not found.",
                body=body, depth=0, path=None, noindex=True)


SWA_CONFIG = {
    "trailingSlash": "auto",
    "platform": {"apiRuntime": "node:20"},
    "routes": [
        {"route": "/contact", "rewrite": "/contact/index.html"},
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
    write("contact/index.html", contact_page())
    write("404.html", not_found())
    write("assets/site.css", CSS)
    write("assets/contact.js", CONTACT_JS)
    write("staticwebapp.config.json", json.dumps(SWA_CONFIG, indent=2) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    write("sitemap.xml", sitemap())

    print(f"built {sum(1 for _ in PUB.rglob('*') if _.is_file())} files → {PUB}")


if __name__ == "__main__":
    main()
