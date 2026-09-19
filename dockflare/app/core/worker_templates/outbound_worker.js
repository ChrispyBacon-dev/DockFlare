import { EmailMessage } from "cloudflare:email";

const MAX_ATTACHMENTS = 25;
const MAX_TOTAL_BYTES = 25 * 1024 * 1024;
const MAX_SUBJECT_LENGTH = 998;

function json(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stripHeader(value) {
  return String(value ?? "").replace(/[\r\n\u0000]+/g, " ").trim();
}

function hasInjection(value) {
  return /[\r\n\u0000]/.test(String(value ?? ""));
}

async function safeEqual(a, b) {
  const encoder = new TextEncoder();
  const [da, db] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(String(a ?? ""))),
    crypto.subtle.digest("SHA-256", encoder.encode(String(b ?? ""))),
  ]);
  const va = new Uint8Array(da);
  const vb = new Uint8Array(db);
  let diff = va.length ^ vb.length;
  for (let i = 0; i < va.length; i++) diff |= va[i] ^ (vb[i] || 0);
  return diff === 0;
}

function parseAddress(value) {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (hasInjection(text)) return null;
  const match = text.match(/<([^<>]+)>/);
  const address = (match ? match[1] : text).trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) return null;
  return address;
}

function addressList(value) {
  const items = Array.isArray(value) ? value : value ? [value] : [];
  const seen = [];
  for (const item of items) {
    const address = parseAddress(item);
    if (address && !seen.includes(address)) seen.push(address);
  }
  return seen;
}

function sanitizeFilename(name) {
  return String(name ?? "").replace(/[\r\n\u0000"\\/]/g, "_").slice(0, 255) || "attachment";
}

function sanitizeContentType(value) {
  const text = stripHeader(value);
  if (!/^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+(\s*;.*)?$/i.test(text)) {
    return "application/octet-stream";
  }
  return text.replace(/[\r\n\u0000]/g, "");
}

async function isRateLimited(env, sender) {
  if (!env.RATE_LIMIT_KV) return false;
  const now = new Date();
  const hourKey = `outbound:${sender}:h:${now.toISOString().slice(0, 13)}`;
  const dayKey = `outbound:${sender}:d:${now.toISOString().slice(0, 10)}`;
  const hourLimit = parseInt(env.RATE_LIMIT_PER_HOUR || "50", 10);
  const dayLimit = parseInt(env.RATE_LIMIT_PER_DAY || "200", 10);
  const [hourRaw, dayRaw] = await Promise.all([
    env.RATE_LIMIT_KV.get(hourKey),
    env.RATE_LIMIT_KV.get(dayKey),
  ]);
  const hourCount = parseInt(hourRaw || "0", 10);
  const dayCount = parseInt(dayRaw || "0", 10);
  if (hourCount >= hourLimit || dayCount >= dayLimit) return true;
  await Promise.all([
    env.RATE_LIMIT_KV.put(hourKey, String(hourCount + 1), { expirationTtl: 7200 }),
    env.RATE_LIMIT_KV.put(dayKey, String(dayCount + 1), { expirationTtl: 172800 }),
  ]);
  return false;
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      return json({ error: "method not allowed" }, 405);
    }

    const authHeader = request.headers.get("Authorization") || "";
    const provided = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
    if (!env.AUTH_SECRET || !(await safeEqual(provided, env.AUTH_SECRET))) {
      return json({ error: "unauthorized" }, 401);
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json({ error: "invalid json" }, 400);
    }

    const domain = String(env.DOMAIN_NAME || "").toLowerCase();
    const fromHeaderValue = stripHeader(body.from);
    const fromAddress = parseAddress(body.from);
    if (!fromAddress) {
      return json({ error: "invalid sender" }, 400);
    }
    if (domain) {
      const fromDomain = fromAddress.slice(fromAddress.lastIndexOf("@") + 1).toLowerCase();
      if (fromDomain !== domain) {
        return json({ error: "sender domain not allowed" }, 403);
      }
    }
    if (env.ALLOWED_SENDERS) {
      let allowedSenders = [];
      try {
        allowedSenders = JSON.parse(env.ALLOWED_SENDERS);
      } catch (e) {
        allowedSenders = [];
      }
      if (Array.isArray(allowedSenders) && allowedSenders.length > 0) {
        const normalized = allowedSenders.map((a) => String(a).toLowerCase());
        if (!normalized.includes(fromAddress.toLowerCase())) {
          return json({ error: "sender not allowed" }, 403);
        }
      }
    }

    const toList = addressList(body.to);
    const ccList = addressList(body.cc);
    const bccList = addressList(body.bcc);
    if (toList.length === 0) {
      return json({ error: "invalid recipients" }, 400);
    }

    if (env.RECIPIENT_ALLOWLIST) {
      let allowedRecipients = [];
      try {
        allowedRecipients = JSON.parse(env.RECIPIENT_ALLOWLIST);
      } catch (e) {
        allowedRecipients = [];
      }
      if (Array.isArray(allowedRecipients) && allowedRecipients.length > 0) {
        const normalized = allowedRecipients.map((a) => String(a).toLowerCase());
        const all = toList.concat(ccList, bccList).map((a) => a.toLowerCase());
        if (!all.every((a) => normalized.includes(a))) {
          return json({ error: "recipient not allowed" }, 403);
        }
      }
    }

    if (await isRateLimited(env, fromAddress.toLowerCase())) {
      return json({ error: "rate limit exceeded" }, 429);
    }

    const envelopeRecipients = toList.concat(ccList, bccList).filter(
      (address, index, array) => array.indexOf(address) === index
    );

    const subject = stripHeader(body.subject).slice(0, MAX_SUBJECT_LENGTH);
    const replyTo = addressList(body.replyTo);
    const inReplyTo = stripHeader(body.inReplyTo);
    const references = stripHeader(body.references);
    const messageId = stripHeader(body.messageId);

    const attachments = (Array.isArray(body.attachments) ? body.attachments : []).filter(
      (a) => a && typeof a.data_b64 === "string" && a.data_b64.length > 0
    ).slice(0, MAX_ATTACHMENTS);

    let totalAttachmentBytes = 0;
    for (const att of attachments) {
      totalAttachmentBytes += att.data_b64.length;
    }
    if (totalAttachmentBytes > MAX_TOTAL_BYTES) {
      return json({ error: "attachments too large" }, 413);
    }

    const hasAttachments = attachments.length > 0;
    const innerBoundary = "b" + crypto.randomUUID().replace(/-/g, "");
    const outerBoundary = hasAttachments ? "b" + crypto.randomUUID().replace(/-/g, "") : null;

    let mimeMessage = `From: ${fromHeaderValue || fromAddress}\r\nTo: ${toList.join(", ")}\r\n`;
    if (ccList.length > 0) mimeMessage += `Cc: ${ccList.join(", ")}\r\n`;
    mimeMessage += `Subject: ${subject}\r\n`;
    mimeMessage += `Date: ${new Date().toUTCString()}\r\n`;
    if (replyTo.length > 0) mimeMessage += `Reply-To: ${replyTo[0]}\r\n`;
    if (inReplyTo) mimeMessage += `In-Reply-To: ${inReplyTo}\r\n`;
    if (references) mimeMessage += `References: ${references}\r\n`;
    if (messageId) mimeMessage += `Message-ID: ${messageId}\r\n`;
    mimeMessage += `MIME-Version: 1.0\r\n`;

    const textBody = String(body.text || (body.html ? "" : "(no content)"));
    const htmlBody = typeof body.html === "string" ? body.html : "";

    if (hasAttachments) {
      mimeMessage += `Content-Type: multipart/mixed; boundary="${outerBoundary}"\r\n\r\n`;
      mimeMessage += `--${outerBoundary}\r\n`;
      mimeMessage += `Content-Type: multipart/alternative; boundary="${innerBoundary}"\r\n\r\n`;
      if (textBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/plain; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${textBody}\r\n`;
      }
      if (htmlBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${htmlBody}\r\n`;
      }
      mimeMessage += `--${innerBoundary}--\r\n`;

      for (const att of attachments) {
        const contentType = sanitizeContentType(att.content_type);
        const filename = sanitizeFilename(att.filename);
        const encodedName = encodeURIComponent(filename);
        mimeMessage += `\r\n--${outerBoundary}\r\n`;
        mimeMessage += `Content-Type: ${contentType}; name="=?UTF-8?Q?${encodedName.replace(/[?=]/g, "")}?="\r\n`;
        mimeMessage += `Content-Transfer-Encoding: base64\r\n`;
        mimeMessage += `Content-Disposition: attachment; filename="=?UTF-8?Q?${encodedName.replace(/[?=]/g, "")}?="; filename*=UTF-8''${encodedName}\r\n\r\n`;
        const b64 = att.data_b64.replace(/[^A-Za-z0-9+/=]/g, "").replace(/(.{76})/g, "$1\r\n");
        mimeMessage += `${b64}\r\n`;
      }
      mimeMessage += `\r\n--${outerBoundary}--\r\n`;
    } else {
      mimeMessage += `Content-Type: multipart/alternative; boundary="${innerBoundary}"\r\n\r\n`;
      if (textBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/plain; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${textBody}\r\n`;
      }
      if (htmlBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${htmlBody}\r\n`;
      }
      mimeMessage += `--${innerBoundary}--\r\n`;
    }

    try {
      for (const recipient of envelopeRecipients) {
        const message = new EmailMessage(fromAddress, recipient, mimeMessage);
        await env.SEND_EMAIL.send(message);
      }
      return json({ success: true, message_id: messageId || undefined }, 200);
    } catch (e) {
      return json({ success: false, error: e.message }, 500);
    }
  }
};
