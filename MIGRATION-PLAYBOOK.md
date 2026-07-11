# DNS + Website Migration Playbook — M365-managed DNS → Azure DNS + SWA

Proven end-to-end on **derekcoleman.com** (2026-07-10, zero downtime, live
mailbox unaffected). This is the 1:1 method for the **dcassociatesgroup.com**
cutover. Cast: *operator* = Derek (registrar/credential steps only),
*agent* = automation (everything else).

## Phase 0 — Preconditions

- [ ] `az` CLI logged in; `gh` CLI logged in with org access
- [ ] Confirm the domain's registrar: `whois <domain> | grep -i registrar`
      (derekcoleman.com was NameBright; dcassociatesgroup.com may differ)
- [ ] Confirm current DNS host from `dig NS <domain>` —
      `ns*.bdm.microsoftonline.com` ⇒ M365-managed DNS (both domains)
- [ ] A live mailbox exists on the domain ⇒ mail records are the critical path

## Phase 1 — Authoritative DNS inventory (READ-ONLY)

1. `dig NS/SOA/A/AAAA/MX/TXT/CAA <domain>` + common subdomains
   (`www autodiscover selector1/2._domainkey _dmarc enterpriseregistration
   enterpriseenrollment lyncdiscover sip _sip._tls _sipfederationtls._tcp` +
   anything the operator knows about).
2. Re-query EVERYTHING against one of the domain's own nameservers with
   `+norecurse` — recursive answers flatten CNAME chains and hide the real
   record shape. Capture exact TTLs.
   - Trap: zsh doesn't word-split unquoted vars — `while read -r name type`
     from a heredoc, not `for q in "name type"`.
   - AXFR will be refused; `ANY` returns nothing. Enumerate by name+type.
3. Commit the inventory to the repo (`docs/dns-inventory-<date>.txt`).
4. **Rule: never write to the current DNS host.** The old zone stays
   untouched until the NS flip.

## Phase 2 — Site + repo (parallel build)

1. New repo under `Derek-Coleman-Associates-Corporation`, reusing the stack:
   stdlib-only `build.py` → `public/`, `api/` SWA managed functions for the
   contact form, `deploy.yml` → `Azure/static-web-apps-deploy@v1`.
2. Contact API gets its OWN storage account (never share the other site's):
   Table `contactform` + Queue `contactform-notify`; connection string in SWA
   app setting `CONTACT_STORAGE_CONNECTION`.
3. Provision: resource group → SWA (Free) → storage → table/queue →
   app settings → `az staticwebapp secrets list` → `gh secret set
   AZURE_STATIC_WEB_APPS_API_TOKEN` → push → verify Actions deploy green.
4. Smoke test on the `*.azurestaticapps.net` host: pages 200, POST
   `/api/contact` 200, row lands in the table.
5. Optional staging: `deployment_environment: ${{ github.ref_name != 'main'
   && 'staging' || '' }}` in deploy.yml; staging branch → named environment
   (Free tier includes 3). **Never the inverted form** (`== 'main' && '' ||
   'staging'`) — the `&&` branch is falsy so `||` always yields `'staging'`
   and main pushes silently deploy to staging (real bug we hit).

## Phase 3 — Parallel Azure DNS zone

1. `az network dns zone create` (note the four assigned nameservers).
2. Recreate EVERY inventoried record, TTL-exact. Traps:
   - TXT: one record-set at the apex holds many values (`add-record` per value).
   - `record-set <type> update --set ttl=` after `add-record` to fix TTLs.
   - Values with `;`/spaces (DMARC) need careful quoting.
3. Register SWA custom domains to get validation tokens
   (`az staticwebapp hostname set --validation-method dns-txt-token`, apex
   AND www) and place `_dnsauth` / `_dnsauth.www` TXTs in the new zone.
4. Apex record = Azure DNS **alias A** targeting the SWA resource
   (`az network dns record-set a create --target-resource <swa-id>`);
   www = CNAME to the default hostname.
5. The old site host records (Vercel/Typedream) are intentionally superseded
   — flag this to the operator explicitly before the flip.

## Phase 4 — Parity proof (the gate)

Diff every name+type: old NS vs new NS answers (`dig @<ns> +norecurse +short`,
sorted). **Every DIFF must be intentional and nameable.** For derekcoleman.com:
15/15 preserved records matched; 4 diffs = apex→SWA, www→SWA, 2 new _dnsauth.
Show the operator the matrix and STOP.

## Phase 5 — NS flip (OPERATOR ONLY)

Registrar dashboard → domain → Nameservers → replace all four with the Azure
zone's `ns*-0X.azure-dns.*` set. Nothing else. M365 admin will warn that DNS
is no longer Microsoft-managed — expected; do NOT remove the domain from M365.

**Mail continuity logic:** the mailbox lives in Exchange Online, not in DNS.
Both zones give byte-identical answers for MX/SPF/DKIM/DMARC/autodiscover, so
mid-propagation delivery works via either zone. Zero-blink by construction.

## Phase 6 — Post-flip verification

- [ ] `dig NS <domain>` via 8.8.8.8 / 1.1.1.1 / 9.9.9.9 → Azure NS
      (derekcoleman.com propagated on all three within ~1 hour)
- [ ] SWA custom domains: `Validating` → `Ready` (self-completes once public
      DNS resolves via the new zone; 15–60 min; if it sat >48h pre-flip and
      errored, delete + re-add the hostname and refresh the _dnsauth TXT)
- [ ] `curl -I https://<domain>` and `https://www.<domain>` → 200, managed
      cert issued (SWA/DigiCert, automatic)
- [ ] MX/SPF/DKIM/DMARC via public resolvers == pre-flip values
- [ ] Operator send-and-receive mail test (in + out)
- [ ] TTL note: old-NS caches can serve stale answers up to the registry NS
      TTL (48h worst case) — harmless here because both zones agree on
      everything except the site host records.

## Phase 7 — Aftercare

- [ ] Ops log entry in `pc-remediation/STATUS.md`
- [ ] Mail-security hardening (now that we own the zone): ramp DMARC
      `p=none` → `p=quarantine` → `p=reject` once rua reports look clean;
      verify the `rua=` mailbox actually exists; consider MTA-STS + TLS-RPT.
- [ ] Keep the old-zone inventory file forever — it is the rollback recipe
      (registrar → point NS back at the old host's servers).

## dcassociatesgroup.com deltas to expect

- Website currently on Typedream (not Vercel) — same supersession pattern.
- M365 tenant records identical in shape (same tenant style records).
- The SWA (`dca-website`) and repo already exist — Phases 2 is mostly done;
  start at Phase 1 (inventory) and Phase 3 (zone).
- No `/support` subdomain exists today (known fleet-wide 404 cause) — decide
  whether to add it during the rebuild.
