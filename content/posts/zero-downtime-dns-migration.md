---
title: Zero-Downtime DNS Migration: Moving a Live Domain from M365 DNS to Azure DNS
date: 2026-07-10
category: tech
excerpt: The parallel-zone method — recreate every record TTL-exact, prove parity with dig diffs, then make the nameserver flip the only moving part. Mail keeps flowing the whole time.
image: assets/blog/parallel-zone-cutover.svg
---

This domain — the one you're reading right now — just moved from Microsoft
365-managed DNS to Azure DNS with a live mailbox on it the whole time. Here's
the method, which works for any DNS host migration where something
business-critical (usually email) can't blink.

## The core idea: build everything, flip one thing

A DNS migration goes wrong when the cutover has more than one moving part.
The fix is to make the nameserver delegation the *only* change:

1. **Inventory the live zone authoritatively.** Not from your notes — from
   the authoritative servers, with TTLs. Recursive resolvers lie by
   flattening CNAME chains; query the zone's own nameservers.
2. **Build a complete parallel zone** at the new host. Every record,
   byte-identical values, matching TTLs. The new zone serves no traffic yet.
3. **Prove parity before flipping.** Diff every record type between the old
   and new nameservers. Intentional changes (a new website host) should be
   the *only* diffs, and you should be able to name each one.
4. **Flip NS at the registrar.** During propagation, resolvers see either
   zone — and both give identical answers for everything that matters.

```python
# the parity gate, conceptually
for name, rtype in inventory:
    prod  = dig(old_ns, name, rtype)
    azure = dig(new_ns, name, rtype)
    assert prod == azure or (name, rtype) in INTENTIONAL_DIFFS
```

## Why mail survives

The mailbox doesn't live in DNS — it lives in Exchange Online. DNS only
tells other mail servers where to deliver (MX) and how to trust you
(SPF, DKIM, DMARC). If those records are identical in both zones, then
mid-propagation a sending server can resolve via *either* zone and get the
*same* answer. There is no moment where mail has nowhere to go.

Three details people miss:

- **DKIM selectors are CNAMEs into your tenant** — copy them exactly,
  including the `onmicrosoft.com` targets.
- **The M365 device-management records** (`enterpriseregistration`,
  `enterpriseenrollment`, `autodiscover`) need to come along or Outlook
  profile setup and Intune enrollment quietly break later.
- **Don't remove the domain from M365 admin.** The admin center will warn
  that DNS is no longer Microsoft-managed. That's fine — the records still
  exist, just hosted elsewhere.

## The one trap: certificate validation timing

The new website host (Azure Static Web Apps here) validates custom domains
by querying *public* DNS — which still resolves through the old nameservers
until you flip. So domain validation sits in "Validating" until cutover
completes. Expected, not broken. Place the validation TXT records in the
new zone ahead of time and validation self-completes minutes after the flip.

---

Total downtime for this site's migration: zero. Mail interruption: zero.
The flip itself: one registrar form.
