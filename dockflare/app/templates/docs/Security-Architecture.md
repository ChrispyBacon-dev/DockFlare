# DockFlare Security Architecture & Hardening

This document explains how DockFlare secures both the Master node and enrolled Agents in DockFlare 3.0+. It complements the security audit by cataloging the safeguards built into DockFlare and outlining recommended operational practices.

## 1. Control Plane Trust Model

- **Master as Source of Truth** – The DockFlare Master holds all Cloudflare credentials and policy definitions. Agents never manage API tokens; they execute instructions received over an authenticated channel.
- **Per-Agent API Keys** – Enrolment requires a unique API key minted by the Master. Keys are stored in the encrypted `agent_keys.dat` store along with metadata (owner, timestamps, status) so they can be rotated or revoked at any time.
- **Master API Protection** – Administrative endpoints (web UI, `/api/v2/*`) require either a valid session or the master API key. Tokens are redacted from responses and logs and can be rotated without restarting the stack.

## 2. Encrypted Configuration & Key Management

- **Encrypted `dockflare_config.dat`** – Cloudflare credentials, UI accounts, tunnel defaults, and the master key are kept in an encrypted blob protected by `dockflare.key`.
- **Encrypted Agent Registry** – Agent API keys and their audit metadata live in `agent_keys.dat`, encrypted with the same Fernet key. Sensitive material no longer appears in `state.json`.
- **Automatic Restart on Restore** – When a backup archive is restored, DockFlare writes the encrypted artefacts, reloads runtime state, drops a restart flag, and exits. Docker’s restart policy brings the container back immediately with the new configuration.
- **Plain `state.json` for observability** – `state.json` remains plaintext so operators can inspect rules and agents. Encrypted files remain authoritative for secrets.

## 3. Backup & Restore Guarantees

- **Archive Contents** – Each backup archive (`dockflare_backup_*.zip`) contains `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json`, and a `manifest.json` with checksums and version metadata. No additional files are required to rebuild a master node.
- **Automated Restore Flow** – Restoring via the setup wizard or the Settings page writes the artefacts, reloads runtime caches, and forces a container restart so the encrypted configuration is applied immediately.
- **Legacy Compatibility** – Uploading a standalone `state.json` is still supported for troubleshooting or partial migrations. DockFlare imports the runtime state but retains the existing encrypted configuration, avoiding accidental credential resets.

## 4. Network & Communication Security

- **Cloudflare Tunnel Transport** – Agents expose no inbound ports. All traffic traverses the Cloudflare tunnel managed by the Master, reducing the attack surface on remote hosts.
- **Authenticated Agent Calls** – Agent REST calls include their API key and are bound to their recorded agent ID. Token mismatches or revoked keys are rejected.
- **Redis Backplane** – DockFlare relies on Redis for caching, log streaming, and cross-thread signalling. The recommended compose stack keeps Redis on a dedicated `dockflare-internal` network so workloads on `cloudflare-net` cannot reach it directly. Secure external Redis services with auth/TLS if you use them.
- **Least-privilege runtime** – Both the master and agents run as the `dockflare` user (UID/GID 65532) and talk to Docker exclusively through the bundled socket proxy, keeping the exposed API surface minimal.

## 5. Authentication & Authorization

- **Hardened UI Login** – The Pre-Flight wizard forces creation of a UI administrator account. Password login can be disabled, but **this is strongly discouraged** due to Docker network security implications (see warning below).
- **Session Management** – Flask-Login sessions are tied to the encrypted configuration. Restoring a backup or rotating credentials invalidates existing sessions automatically.
- **Agent ACLs** – Each agent record tracks tunnel assignment, heartbeat timestamps, and pending commands. The Master only delivers commands to agents presenting the correct token and enrolled status.

### ⚠️ Important: "Disable Password Login" Security Warning

DockFlare includes a "Disable Password Login" setting intended for advanced deployments where DockFlare itself is protected by an external authentication layer (like Cloudflare Access). **We strongly advise against using this feature** for most deployments.

**Security risks when enabled:**
- **All API endpoints become accessible without authentication** when this setting is enabled
- **Docker network exposure:** Even if DockFlare is behind Cloudflare Access on the public internet, containers on the same Docker network can bypass external authentication and access DockFlare's API directly
- **No authentication enforcement:** The application assumes external authentication is handling security

**Attack vector example:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Recommended approach:**
Instead of disabling password authentication, use one of these secure options:
1. **Local DockFlare credentials** - Simple password authentication built into DockFlare
2. **OAuth/OIDC providers** - Configure Google, GitHub, Azure AD, or other identity providers for easy single sign-on without sacrificing security

Both options provide proper authentication while maintaining the convenience of SSO. The OAuth option gives you the single sign-on experience without the security risks of disabled authentication.

**Bottom line:** Unless you have a very specific, well-understood security architecture with network isolation, keep password login enabled and use OAuth for convenience.

## 6. Audit & Operational Visibility

- **Metadata Tracking** – Agent keys record `created_at`, `last_used_at`, `bound_agent_id`, status, and revocation events. `state.json` mirrors agent last-seen timestamps for at-a-glance health checks.
- **Log Streaming** – Real-time logs stream via Redis pub/sub. Sensitive values (tokens, keys) are redacted before reaching the client.
- **Status APIs** – `/api/v2/overview` consolidates tunnel, agent, and configuration health for monitoring systems or GitOps workflows.

## 7. Deployment Recommendations

| Area | Recommendation |
| --- | --- |
| Docker Volumes | Persist `/app/data` (encrypted config, keys, state). Persist `/app/logs` if file logging is enabled, and ensure host mounts are writable by UID/GID 65532 or your overridden build args. |
| Redis | Run `redis:7-alpine` alongside DockFlare on a private network (`dockflare-internal`) or point `REDIS_URL` to a hardened instance (auth/TLS). Avoid exposing Redis publicly. Use `REDIS_DB_INDEX` to isolate DockFlare data from other containers sharing the same Redis instance. |
| Backups | Download the `.zip` regularly and store it with `dockflare.key`. Both files are required to decrypt the configuration on restore. |
| Agents | Treat API keys like credentials. Deploy them with the socket proxy so only required Docker endpoints are exposed, and remember the container runs as the unprivileged `dockflare` user (UID/GID 65532); align host permissions or rebuild with matching `DOCKFLARE_UID/DOCKFLARE_GID`. |
| Reverse Proxy | Place DockFlare behind Cloudflare Access or another trusted IdP. If you disable password login, ensure upstream authentication is always enforced. |
| Monitoring | Alert on unexpected restarts, missing agent heartbeats, or new key issuance outside maintenance windows. |

## 8. Future Enhancements (Roadmap)

- Optional passphrase protection for the Fernet key at rest.
- Automated agent key rotation with grace periods for staging rollout.
- Granular agent command scopes to separate read-only and mutating operations.

---

DockFlare continues to evolve with security in mind. Stay current with release notes for additional hardening improvements and contribute ideas via the issue tracker if you need further controls.
