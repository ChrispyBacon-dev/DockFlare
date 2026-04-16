import { EmailMessage } from "cloudflare:email";

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }
    const authHeader = request.headers.get("Authorization");
    if (authHeader !== `Bearer ${env.AUTH_SECRET}`) {
      return new Response("Unauthorized", { status: 401 });
    }
    const body = await request.json();
    const toHeader = Array.isArray(body.to) ? body.to.join(", ") : body.to;
    const rawTo = Array.isArray(body.to) ? body.to[0] : body.to;
    const addrMatch = typeof rawTo === 'string' ? rawTo.match(/<([^>]+)>/) : null;
    const toAddress = addrMatch ? addrMatch[1] : (typeof rawTo === 'string' ? rawTo.trim() : rawTo);

    const attachments = Array.isArray(body.attachments) ? body.attachments.filter(a => a && a.data_b64) : [];
    const hasAttachments = attachments.length > 0;

    const innerBoundary = "b" + crypto.randomUUID().replace(/-/g, "");
    const outerBoundary = hasAttachments ? "b" + crypto.randomUUID().replace(/-/g, "") : null;


    let mimeMessage = `From: ${body.from}\r\nTo: ${toHeader}\r\n`;
    if (body.cc) mimeMessage += `Cc: ${Array.isArray(body.cc) ? body.cc.join(", ") : body.cc}\r\n`;
    if (body.bcc) mimeMessage += `Bcc: ${Array.isArray(body.bcc) ? body.bcc.join(", ") : body.bcc}\r\n`;
    mimeMessage += `Subject: ${body.subject}\r\n`;
    mimeMessage += `Date: ${new Date().toUTCString()}\r\n`;
    if (body.replyTo) mimeMessage += `Reply-To: ${body.replyTo}\r\n`;
    if (body.inReplyTo) mimeMessage += `In-Reply-To: ${body.inReplyTo}\r\n`;
    if (body.references) mimeMessage += `References: ${body.references}\r\n`;
    if (body.messageId) mimeMessage += `Message-ID: ${body.messageId}\r\n`;
    mimeMessage += `MIME-Version: 1.0\r\n`;

    const textBody = body.text || (body.html ? "" : "(no content)");

    if (hasAttachments) {

      mimeMessage += `Content-Type: multipart/mixed; boundary="${outerBoundary}"\r\n\r\n`;

      mimeMessage += `--${outerBoundary}\r\n`;
      mimeMessage += `Content-Type: multipart/alternative; boundary="${innerBoundary}"\r\n\r\n`;
      if (textBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/plain; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${textBody}\r\n`;
      }
      if (body.html) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${body.html}\r\n`;
      }
      mimeMessage += `--${innerBoundary}--\r\n`;

      for (const att of attachments) {
        const ct = att.content_type || 'application/octet-stream';
        const fn = att.filename || 'attachment';
        mimeMessage += `\r\n--${outerBoundary}\r\n`;
        mimeMessage += `Content-Type: ${ct}; name="${fn}"\r\n`;
        mimeMessage += `Content-Transfer-Encoding: base64\r\n`;
        mimeMessage += `Content-Disposition: attachment; filename="${fn}"\r\n\r\n`;
        // Chunk base64 at 76 chars per line (RFC 2045)
        const b64 = att.data_b64.replace(/(.{76})/g, '$1\r\n');
        mimeMessage += `${b64}\r\n`;
      }
      mimeMessage += `\r\n--${outerBoundary}--\r\n`;
    } else {

      mimeMessage += `Content-Type: multipart/alternative; boundary="${innerBoundary}"\r\n\r\n`;
      if (textBody) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/plain; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${textBody}\r\n`;
      }
      if (body.html) {
        mimeMessage += `--${innerBoundary}\r\nContent-Type: text/html; charset="utf-8"\r\nContent-Transfer-Encoding: 8bit\r\n\r\n${body.html}\r\n`;
      }
      mimeMessage += `--${innerBoundary}--\r\n`;
    }

    const message = new EmailMessage(body.from, toAddress, mimeMessage);
    try {
      await env.SEND_EMAIL.send(message);
      return new Response(JSON.stringify({ success: true, message_id: body.messageId }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    } catch (e) {
      return new Response(JSON.stringify({ success: false, error: e.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
