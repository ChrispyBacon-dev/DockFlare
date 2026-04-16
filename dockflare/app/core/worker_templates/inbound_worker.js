async function signPayload(secret, payloadString) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signatureBuffer = await crypto.subtle.sign("HMAC", key, encoder.encode(payloadString));
  const signatureArray = Array.from(new Uint8Array(signatureBuffer));
  return signatureArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function dispatchWebhook(env, payload) {
  const payloadString = JSON.stringify(payload);
  const signatureHex = await signPayload(env.WEBHOOK_SECRET, payloadString);
  const response = await fetch(env.WEBHOOK_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-DockFlare-Signature": signatureHex,
      "X-DockFlare-Message-Id": payload.message_id,
      "X-DockFlare-Domain": env.DOMAIN_NAME
    },
    body: payloadString,
    signal: AbortSignal.timeout(10000)
  });
  return response;
}

export default {
  // ── Inbound email handler ──────────────────────────────────────────────────-.--...--
  async email(message, env, ctx) {
    try {
      const catchAllEnabled = env.CATCH_ALL_ENABLED === 'true';
      if (catchAllEnabled) {
        const domain = (env.DOMAIN_NAME || '').toLowerCase();
        if (!message.to.toLowerCase().endsWith('@' + domain)) {
          message.setReject("Recipient not allowed");
          return;
        }
      } else {
        const allowedRecipients = JSON.parse(env.ALLOWED_RECIPIENTS || '[]');
        if (!allowedRecipients.includes(message.to)) {
          message.setReject("Recipient not allowed");
          return;
        }
      }

      // Check quota KV before accepting — reject at SMTP level so sender gets a bounce
      if (typeof env.QUOTA_KV !== 'undefined') {
        try {
          const state = await env.QUOTA_KV.get(message.to, "json");
          if (state?.blocked) {
            message.setReject("550 5.2.2 Mailbox full");
            return;
          }
        } catch (kvErr) {
          // KV unavailable — fall through, webhook safety net handles enforcement
          console.warn(`KV quota check failed for ${message.to}: ${kvErr.message}`);
        }
      }

      const messageId = crypto.randomUUID();
      const r2Key = `temp_cache/${messageId}.eml`;
      const receivedAt = new Date().toISOString();

      // Upload to R2 first — email is now safely buffered regardless of what happens next
      const rawBytes = await new Response(message.raw).arrayBuffer();
      await env.EMAIL_BUCKET.put(r2Key, rawBytes, {
        customMetadata: {
          from: message.from,
          to: message.to,
          subject: message.headers.get("subject") || "",
          receivedAt: receivedAt
        }
      });

      const payload = {
        message_id: messageId,
        from: message.from,
        to: message.to,
        subject: message.headers.get("subject") || "",
        received_at: receivedAt,
        r2_key: r2Key,
        size_bytes: message.rawSize || 0
      };

      try {
        const webhookResponse = await dispatchWebhook(env, payload);
        if (webhookResponse.ok) {
          const body = await webhookResponse.json().catch(() => ({}));
          if (body.reason === 'over_hard_quota') {
            // Mail Manager rejected the email (hard quota exceeded) and already cleaned
            // up R2 + the DB entry. Reject at SMTP level so sender gets an NDR bounce.
            message.setReject("550 5.2.2 Mailbox full");
            return;
          }
          // On success the mail-manager deletes the R2 file itself after processing.
        } else {
          // DockFlare returned an error — leave email in R2 for cron retry.
          // The email is safely buffered and will be delivered
          // automatically when DockFlare is healthy again.
          console.warn(`Webhook returned ${webhookResponse.status} for ${messageId} — buffered in R2 for retry`);
        }
      } catch (webhookErr) {
        // DockFlare is unreachable (offline, timeout, network error).
        // Email is already in R2. Cron will retry. Do NOT reject.
        console.warn(`Webhook unreachable for ${messageId} — buffered in R2 for retry: ${webhookErr.message}`);
      }

    } catch (err) {
      // Only reject if failed to store the email in R2 (truly unrecoverable). - reminder need some tests still 
      message.setReject(`Worker error: ${err.message}`);
    }
  },

  // ── Cron trigger: retry buffered emails in R2 ─────────────────────────-..-.-.-.-────
  async scheduled(event, env, ctx) {
    console.log("Cron: scanning R2 temp_cache for buffered emails...");

    let cursor;
    let processed = 0;
    let failed = 0;

    do {
      const list = await env.EMAIL_BUCKET.list({
        prefix: "temp_cache/",
        limit: 100,
        cursor: cursor
      });

      for (const object of list.objects) {
        const r2Key = object.key;
        const meta = object.customMetadata || {};
        const messageId = r2Key.replace("temp_cache/", "").replace(".eml", "");

        const payload = {
          message_id: messageId,
          from: meta.from || "",
          to: meta.to || "",
          subject: meta.subject || "",
          received_at: meta.receivedAt || new Date().toISOString(),
          r2_key: r2Key,
          size_bytes: object.size || 0
        };

        try {
          const response = await dispatchWebhook(env, payload);
          if (response.ok) {
            const body = await response.json().catch(() => ({}));
            if (body.reason === 'over_hard_quota') {
              // Mailbox was full when cron retried — webhook already cleaned R2 + set KV block.
              // Count as processed (not a retry-able failure).
              console.warn(`Cron: buffered email ${messageId} rejected (over_hard_quota) — R2 cleaned by Mail Manager`);
              processed++;
            } else {
              console.log(`Cron: delivered buffered email ${messageId} to DockFlare`);
              processed++;
            }
          } else {
            const body = await response.text().catch(() => '');
            console.warn(`Cron: webhook returned ${response.status} for ${messageId}: ${body.slice(0, 100)}`);
            failed++;
          }
        } catch (err) {
          // DockFlare still offline — will retry on next cron run
          console.warn(`Cron: DockFlare still unreachable for ${messageId}: ${err.message}`);
          failed++;
        }
      }

      cursor = list.truncated ? list.cursor : undefined;
    } while (cursor);

    console.log(`Cron: done. processed=${processed} failed=${failed}`);
  }
};
