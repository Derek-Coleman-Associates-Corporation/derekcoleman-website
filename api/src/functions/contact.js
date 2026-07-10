/**
 * POST /api/contact — contact-form intake for derekcoleman.com.
 *
 * Accepts JSON {name, email, company, topic, message, website} where
 * "website" is a honeypot (visually hidden on the site; any value ⇒ bot ⇒
 * silently accepted but not stored).
 *
 * Persists every real submission to:
 *   - Azure Table  `contactform`        (this site's own storage account —
 *     NOT the dcassociatesgroup one)
 *   - Azure Queue  `contactform-notify` — plain-text copy for queue-based pickup.
 *
 * Email notification: intentionally NOT sent (no credential-free email path
 * on this SWA). Poll the table instead.
 *
 * Auth: connection string from app setting CONTACT_STORAGE_CONNECTION
 * (set via `az staticwebapp appsettings set`).
 */
"use strict";

const { app } = require("@azure/functions");
const { TableClient } = require("@azure/data-tables");
const { QueueClient } = require("@azure/storage-queue");
const crypto = require("node:crypto");

const TABLE_NAME = "contactform";
const QUEUE_NAME = "contactform-notify";
const TOPICS = ["General", "Consulting", "Speaking", "Other"];
const FALLBACK_EMAIL = "derek@derekcoleman.com";

// ── basic in-memory rate limiting by client IP ────────────────────────────────
// Best-effort: state lives per warm worker instance, which is fine for a
// low-volume personal site — it stops casual abuse, not a distributed attack.
const RATE_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
const RATE_MAX = 5;                    // submissions per IP per window
const hits = new Map();                // ip -> [epoch-ms, ...]

function rateLimited(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < RATE_WINDOW_MS);
  if (recent.length >= RATE_MAX) {
    hits.set(ip, recent);
    return true;
  }
  recent.push(now);
  hits.set(ip, recent);
  // opportunistic cleanup so the map can't grow unbounded
  if (hits.size > 1000) {
    for (const [k, v] of hits) {
      if (v.every((t) => now - t >= RATE_WINDOW_MS)) hits.delete(k);
    }
  }
  return false;
}

function clientIp(request) {
  const fwd = request.headers.get("x-forwarded-for") || "";
  const first = fwd.split(",")[0].trim();
  // SWA/Functions may append a port ("1.2.3.4:12345"); strip it (IPv4 only —
  // bracketed IPv6 is left as-is, still a stable per-client key).
  const m = first.match(/^(\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?$/);
  return m ? m[1] : first || "unknown";
}

// ── validation ────────────────────────────────────────────────────────────────
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validate(body) {
  const errors = [];
  const name = String(body.name || "").trim();
  const email = String(body.email || "").trim();
  const company = String(body.company || "").trim();
  const topic = String(body.topic || "").trim();
  const message = String(body.message || "").trim();

  if (!name || name.length > 200) errors.push("name is required (max 200 chars)");
  if (!email || email.length > 320 || !EMAIL_RE.test(email)) errors.push("a valid email is required");
  if (company.length > 300) errors.push("company is too long (max 300 chars)");
  if (!TOPICS.includes(topic)) errors.push(`topic must be one of: ${TOPICS.join(", ")}`);
  if (!message || message.length > 5000) errors.push("message is required (max 5000 chars)");

  return { errors, clean: { name, email, company, topic, message } };
}

function json(status, obj) {
  return { status, jsonBody: obj };
}

// ── handler ───────────────────────────────────────────────────────────────────
app.http("contact", {
  methods: ["POST"],
  authLevel: "anonymous",
  route: "contact",
  handler: async (request, context) => {
    let body;
    try {
      body = await request.json();
    } catch {
      return json(400, { ok: false, error: "Request body must be JSON." });
    }
    if (!body || typeof body !== "object") {
      return json(400, { ok: false, error: "Request body must be a JSON object." });
    }

    // Honeypot: bots fill the hidden "website" field. Pretend success so the
    // bot learns nothing; store nothing.
    if (String(body.website || "").trim() !== "") {
      context.log("contact: honeypot tripped — dropping submission");
      return json(200, { ok: true });
    }

    const ip = clientIp(request);
    if (rateLimited(ip)) {
      return json(429, { ok: false, error: `Too many submissions — please try again later, or email ${FALLBACK_EMAIL}.` });
    }

    const { errors, clean } = validate(body);
    if (errors.length) {
      return json(400, { ok: false, error: errors.join("; ") });
    }

    const conn = process.env.CONTACT_STORAGE_CONNECTION;
    if (!conn) {
      context.error("contact: CONTACT_STORAGE_CONNECTION app setting is missing");
      return json(500, { ok: false, error: `Server configuration error — please email ${FALLBACK_EMAIL}.` });
    }

    const now = new Date();
    const submittedUtc = now.toISOString();
    const entity = {
      partitionKey: submittedUtc.slice(0, 7), // e.g. "2026-07" — one partition per month
      rowKey: `${submittedUtc}_${crypto.randomUUID()}`,
      name: clean.name,
      email: clean.email,
      company: clean.company,
      topic: clean.topic,
      message: clean.message,
      submittedUtc,
      sourceIp: ip,
      userAgent: request.headers.get("user-agent") || "",
      status: "new",
    };

    // 1) Table row — the durable record.
    try {
      const table = TableClient.fromConnectionString(conn, TABLE_NAME);
      await table.createEntity(entity);
    } catch (err) {
      context.error(`contact: table write failed: ${err.message}`);
      return json(500, { ok: false, error: `Could not save your message — please email ${FALLBACK_EMAIL}.` });
    }

    // 2) Plain-text copy on the notify queue (best-effort; row already saved).
    try {
      // NB: unlike TableClient, QueueClient has no static fromConnectionString —
      // the constructor takes the connection string directly.
      const queue = new QueueClient(conn, QUEUE_NAME);
      const text = [
        "New contact form submission — derekcoleman.com",
        `Submitted: ${submittedUtc}`,
        `Name: ${clean.name}`,
        `Email: ${clean.email}`,
        `Company: ${clean.company || "(none)"}`,
        `Topic: ${clean.topic}`,
        "",
        clean.message,
        "",
        `Table row: ${TABLE_NAME} PartitionKey=${entity.partitionKey} RowKey=${entity.rowKey}`,
      ].join("\n");
      await queue.sendMessage(text);
    } catch (err) {
      context.warn(`contact: queue enqueue failed (row saved): ${err.message}`);
    }

    context.log(`contact: stored submission from ${clean.email} (topic=${clean.topic})`);
    return json(200, { ok: true });
  },
});
