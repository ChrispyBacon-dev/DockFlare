# Content Security Policy (CSP)

## What is a Content Security Policy?

A Content Security Policy (CSP) is a web security standard that helps prevent certain types of attacks, most notably Cross-Site Scripting (XSS) and data injection attacks. It works by telling the browser which sources of content (scripts, styles, images, etc.) are trusted and allowed to be loaded on a web page.

## DockFlare's CSP

The DockFlare application itself has a web interface. To protect this interface and ensure its security, DockFlare implements a strict Content Security Policy on its own UI.

This is an important internal security feature designed to protect you, the administrator, from potential browser-based vulnerabilities when you are using the DockFlare dashboard.

## Scope of the CSP

It is important to understand that DockFlare's CSP applies **only to the DockFlare Web UI itself**.

It does **not** affect, modify, or add any CSP headers to the traffic that is being proxied through your Cloudflare Tunnel to your own applications. If you want to implement a CSP on your own applications, you must configure that within the applications themselves (e.g., by setting the `Content-Security-Policy` HTTP header in your web server or application code).

## Configuration

DockFlare's CSP is an integral part of its security posture and is **not user-configurable**. The policy is carefully crafted to be as restrictive as possible while still allowing the UI to function correctly.

If you are interested in learning more about how Content Security Policies work in general, the [MDN Web Docs on CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) is an excellent resource.
