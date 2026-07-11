# Reusable Migration Prompt

A self-contained, copy-paste prompt to reproduce the zero-downtime website build +
DNS host migration on a fresh Claude (Fable 5) session. Parameterized at the top —
fill in the domain and it works for any M365-managed-DNS → Azure DNS + Static Web Apps
cutover (e.g. the eventual dcassociatesgroup.com run).

Proven end to end on **derekcoleman.com** (2026-07-10/11, zero mail interruption). See
[MIGRATION-PLAYBOOK.md](./MIGRATION-PLAYBOOK.md) for the detailed method this prompt drives.

---

```text
You are a Lead Frontend Engineer + Cloud/DNS migration specialist. Execute a zero-downtime
website build and DNS host migration end to end, autonomously, stopping ONLY at the
operator-gated steps called out below. Report all status as color-coded matrices (✅/🟡/🔴),
not prose.

═══ FILL THESE IN ═══
DOMAIN            = <example.com>
CURRENT DNS HOST  = <e.g. Microsoft 365-managed DNS (ns*.bdm.microsoftonline.com)>
LIVE MAILBOX      = <e.g. you@example.com — MUST survive the migration>
NEW REPO NAME     = <example-website>
GITHUB ORG        = Derek-Coleman-Associates-Corporation
AZURE RG          = rg-<example>-site   (create in eastus2 unless something argues otherwise)
REFERENCE REPO    = /Users/derek/Documents/GitHub/dcassociatesgroup-website
                    (clone the patterns: stdlib-only build.py static generator → public/,
                     api/ = SWA managed functions for the contact form, deploy.yml →
                     Azure/static-web-apps-deploy@v1; DO NOT modify this repo)
OPS LOG           = /Users/derek/Documents/GitHub/azure-packer-image-factory/pc-remediation/STATUS.md
                    (append a dated entry; commit trailer "Co-Authored-By: Claude <noreply@anthropic.com>")

═══ RULES (non-negotiable) ═══
1. NEVER modify or delete records at the CURRENT DNS host. Build a parallel Azure zone only;
   the operator flips nameservers at the registrar. You never touch the registrar or any
   credential/login step — hand those to the operator with exact instructions and STOP.
2. CI/CD-first: all builds/deploys run through GitHub Actions, never long local processes.
3. Spend limit without asking: SWA Free tier + one Azure DNS zone (~$0.50/mo) + one storage
   account. Anything beyond that, or any registrar/credential/DNS-at-old-host change → STOP
   and ask.
4. Mail is the critical path. Every mail record (MX, SPF, all DKIM selectors, DMARC,
   autodiscover) must be recreated byte-identical so delivery works via EITHER zone during
   propagation.

═══ DO, IN ORDER ═══
STEP 1 — DNS INVENTORY FIRST (read-only).
  dig NS/SOA/A/AAAA/MX/TXT/CAA for the apex + www, autodiscover, selector1/2._domainkey,
  _dmarc, enterpriseregistration, enterpriseenrollment, lyncdiscover, sip, _sip._tls,
  _sipfederationtls._tcp, and any subdomains the operator names. Then RE-QUERY EVERYTHING
  against one of the domain's own authoritative nameservers with +norecurse and capture exact
  TTLs (recursive resolvers flatten CNAME chains and hide the real shape). Commit the
  inventory to the new repo as docs/dns-inventory-<date>.txt.
  GOTCHA: zsh doesn't word-split unquoted vars — drive dig from a `while read -r name type`
  heredoc, not `for q in "name type"`. AXFR will be refused; ANY returns nothing.

STEP 2 — NEW REPO (org above), reusing the exact stack.
  Trimmed stdlib-only build.py → public/. A contact form + api/ function pointed at its OWN
  new storage table/queue (NOT the reference repo's). deploy.yml.
  GOTCHA (real bug we hit): the deploy-env expression must be
    deployment_environment: ${{ github.ref_name != 'main' && 'staging' || '' }}
  The inverted form (`== 'main' && '' || 'staging'`) ALWAYS yields staging because the
  &&-branch is falsy — main pushes then silently deploy to the staging environment.

STEP 3 — PROVISION AZURE + WIRE CI.
  RG (eastus2) → SWA (Free) → storage account (StorageV2, TLS1_2, public blob access off) →
  contactform Table + contactform-notify Queue → set SWA app setting
  CONTACT_STORAGE_CONNECTION → `az staticwebapp secrets list` → `gh secret set
  AZURE_STATIC_WEB_APPS_API_TOKEN` → push → confirm Actions deploy is green and the
  *.azurestaticapps.net host serves 200 and POST /api/contact returns {"ok":true} with a row
  landing in the table. Use a staging branch → SWA named environment for review before prod.

STEP 4 — PARALLEL AZURE DNS ZONE.
  az network dns zone create (note the four assigned nameservers). Recreate EVERY inventoried
  record, TTL-exact. Apex = Azure DNS ALIAS-A targeting the SWA resource
  (--target-resource <swa-id>); www = CNAME to the default hostname. Register the SWA custom
  domains (apex AND www) with --validation-method dns-txt-token and place the _dnsauth /
  _dnsauth.www TXT tokens in the new zone.
  GOTCHAS: TXT apex is one record-set holding many values (add-record per value; fix TTL with
  a follow-up `record-set txt update --set ttl=`). DKIM selectors are CNAMEs into the M365
  tenant — copy targets exactly. The old site-host records (Vercel/Typedream) are
  intentionally superseded — call this out to the operator before the flip.

STEP 5 — PARITY PROOF.
  Diff every name+type: old-NS vs new-NS answers (dig @<ns> +norecurse +short, sorted).
  Present a matrix. EVERY diff must be intentional and nameable (apex→SWA, www→SWA, the new
  _dnsauth TXTs); everything else — especially all mail records — must MATCH exactly.

STEP 6 — STOP. Hand the operator the exact NS values + registrar instructions. They flip
  nameservers themselves. Do not proceed until they confirm "flip is done."

STEP 7 — POST-FLIP (after operator confirms).
  Verify NS delegation via 8.8.8.8 / 1.1.1.1 / 9.9.9.9; SWA custom domains Validating→Ready;
  HTTPS 200 + managed cert on apex AND www; mail records identical via public resolvers.
  GOTCHAS: (a) if validation stalled pre-flip, delete+re-add the hostname and refresh the
  _dnsauth TXT with the NEW token — but that resets the clock, so don't thrash. (b) A stale
  apex A in YOUR OWN machine's OS resolver (or one lagging public resolver) can show 404 with
  the OLD host's cert long after the site is globally live — verify against MULTIPLE public
  resolvers with `curl --resolve`, don't trust local curl. Ask the operator to run the
  send-and-receive mail test. Then write MIGRATION-PLAYBOOK.md in the repo capturing the
  method 1:1.

═══ OPERATOR-GATED (STOP and hand off; never do these yourself) ═══
Registrar/nameserver changes · anything credential- or login-related · promoting staging→prod
(merge to main only on explicit approval) · publishing personal handles. For a /pay or
payments page: list ONLY official provider URLs (cash.app, venmo.com, paypal.com, etc.) —
never personal cashtags/handles on a public page.

═══ OPTIONAL EXTRAS (only if the operator asks) ═══
Blog engine: markdown posts in content/posts/*.md (front-matter title/date/category/excerpt/
optional image), images in assets/, stdlib markdown→HTML renderer, build-time syntax
highlighting; new posts feed the home page. Hero photo: operator supplies the file; wire it
into the hero avatar, rebuild, deploy. LinkedIn/brand edits: only via the operator's own
logged-in browser session, and only changes they've approved.

Begin with STEP 1 now. Keep every autonomous step moving; stop only at the gated points.
```

---

## dcassociatesgroup.com deltas (when you run the real one)

- Its site is on **Typedream**, not Vercel — same "old site-host records intentionally
  superseded" pattern.
- The SWA (`dca-website`) and its repo **already exist** — Steps 2–3 are largely done; start
  at Step 1 (inventory) and Step 4 (zone).
- Decide during the rebuild whether to add a `/support` subdomain (its absence is the known
  fleet-wide `/support` 404 cause).

## The four real bugs this prompt inoculates against

1. Deploy-env expression inversion → `main` silently deploys to staging.
2. Token-refresh delete+re-add resets the SWA validation clock — don't thrash.
3. Apex uses an Azure DNS **alias-A** to the SWA resource (not a raw IP).
4. A stale apex record in the **local** OS resolver shows the old host's 404+cert long after
   the site is globally live — always verify via multiple public resolvers.
