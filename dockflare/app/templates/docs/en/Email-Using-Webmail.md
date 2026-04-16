# Using Webmail (PWA)

DockFlare includes a modern, responsive webmail client that allows you to manage your emails from any device.

## Accessing Webmail

There are two ways to log in to Webmail:

1.  **SSO (Single Sign-On):** If you are an admin logged into the DockFlare Master UI, click **Open Webmail** on the Email page. You will be automatically authenticated and logged into your mailboxes.
2.  **Direct Login:** Navigate to `https://mail.yourdomain.com`. If you have set a password for your mailbox in the Master UI, you can log in directly using your email address and password.

## Installing as a PWA

The DockFlare Webmail is a **Progressive Web App (PWA)**. This means you can install it on your device for an app-like experience.

### On Mobile (iOS/Android) (currently under development mobile support is limited)
*   Open the webmail URL in your mobile browser.
*   **iOS:** Tap the "Share" icon and select **Add to Home Screen**.
*   **Android:** Tap the three dots and select **Install App** or **Add to Home Screen**.

### On Desktop (Chrome/Edge/Brave)
*   Look for the "Install" icon in the address bar (usually a small monitor with a down arrow).
*   Click **Install**.

## Key Features

*   **Search:** Use the search bar to find emails. DockFlare uses Full-Text Search (FTS5) to index your subjects, senders, and message bodies locally.
*   **Push Notifications:** Enable notifications in the Webmail settings to receive real-time alerts for new emails on your desktop or mobile device.

## Security

*   **EdDSA Authentication:** Webmail uses high-security Ed25519 JSON Web Tokens (JWT) issued by the DockFlare Master for all API interactions.
*   **HTML Sanitization:** All incoming HTML emails are sanitized (using DOMPurify) before rendering to protect you from cross-site scripting (XSS) and tracking pixels.
