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
  async email(message, env, ctx) {
    try {
      let resolvedMailbox = null;
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
          let aliasRecord = null;
          try {
            aliasRecord = await env.QUOTA_KV.get('alias::' + message.to, 'json');
          } catch (_) {}

          if (!aliasRecord) {
            message.setReject("Recipient not allowed");
            return;
          }
          resolvedMailbox = aliasRecord.mailbox;
        }
      }

      if (typeof env.QUOTA_KV !== 'undefined') {
        try {
          const quotaTarget = resolvedMailbox || message.to;
          const state = await env.QUOTA_KV.get(quotaTarget, "json");
          if (state?.blocked) {
            message.setReject("550 5.2.2 Mailbox full");
            return;
          }
        } catch (kvErr) {
          console.warn(`KV quota check failed for ${message.to}: ${kvErr.message}`);
        }
      }

      const messageId = crypto.randomUUID();
      const r2Key = `temp_cache/${messageId}.eml`;
      const receivedAt = new Date().toISOString();

      const rawBytes = await new Response(message.raw).arrayBuffer();
      await env.EMAIL_BUCKET.put(r2Key, rawBytes, {
        customMetadata: {
          from: message.from,
          to: message.to,
          resolved_mailbox: resolvedMailbox || message.to,
          via_alias: resolvedMailbox ? "1" : "0",
          subject: message.headers.get("subject") || "",
          receivedAt: receivedAt
        }
      });

      const payload = {
        message_id: messageId,
        from: message.from,
        to: message.to,
        resolved_mailbox: resolvedMailbox || message.to,
        via_alias: !!resolvedMailbox,
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
            message.setReject("550 5.2.2 Mailbox full");
            return;
          }
        } else {
          console.warn(`Webhook returned ${webhookResponse.status} for ${messageId} — buffered in R2 for retry`);
        }
      } catch (webhookErr) {
        console.warn(`Webhook unreachable for ${messageId} — buffered in R2 for retry: ${webhookErr.message}`);
      }

    } catch (err) {
      message.setReject(`Worker error: ${err.message}`);
    }
  },

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
          resolved_mailbox: meta.resolved_mailbox || meta.to || "",
          via_alias: meta.via_alias === "1",
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
          console.warn(`Cron: DockFlare still unreachable for ${messageId}: ${err.message}`);
          failed++;
        }
      }

      cursor = list.truncated ? list.cursor : undefined;
    } while (cursor);

    console.log(`Cron: done. processed=${processed} failed=${failed}`);
  }
};
