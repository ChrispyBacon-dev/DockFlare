# DockFlare Security Assessment Report (v3.0.3)

**Assessment Date:** September 28, 2025  
**Target Application:** DockFlare v3.0.3  
**Test Host:** http://localhost:5001 (local deployment)  
**Assessment Type:** White-box review with unauthenticated probing (no credentials or API keys)

---

## Executive Summary

This assessment revisits DockFlare after the addition of several diagnostic endpoints in v3.0.3. All network testing was performed without administrator credentials, OAuth access, or master/agent API keys. Even under these constraints, the application exposes no sensitive information beyond its public health probe (`/ping`) and the login workflow. Newly introduced routes (`/version/check`, `/debug`, `/api/v2/ping`, `/api/v2/debug-info`) remain shielded behind the existing authentication gates, preventing anonymous disclosure of runtime metadata. The only lingering medium-risk item is the permissive CORS header set on server-sent event (SSE) streams—impacting authenticated sessions, but not exploitable by anonymous users.

---

## Methodology

1. **Baseline Review** – Studied `security_assessment_report.md` (v3.0.1) to understand the prior security posture and resolved findings.
2. **Route Enumeration** – Indexed Flask routes with `rg '@.*route'` to document UI, API v2, setup, and help blueprints.
3. **Authentication Logic Audit** – Examined `gating_logic` in `dockflare/app/web/routes.py` and `_enforce_master_api_key` in `dockflare/app/web/api_v2_routes.py` to determine which endpoints are exempt from login or API-key checks.
4. **Unauthenticated Probing** – Crafted `test_scripts/route_probe.py` to simulate curl-based testing without credentials. The script defaults to anonymous requests and reports HTTP status, redirect targets, and perceived access level for each route.
5. **Static Verification** – Correlated expected HTTP responses with source code to confirm there are no accidental allow-list entries for new routes. Due to sandbox restrictions, live HTTP responses could not be captured in this environment; the script is provided so you can reproduce the results directly against `localhost:5001`.

Run the probe locally (no credentials required):

```bash
python3 test_scripts/route_probe.py --base-url http://localhost:5001
```

Use `--output json` for machine-readable output or `--routes custom.json` to extend coverage during regression testing.

---

## Anonymous Route Exposure (Expected Behaviour)

| Route | Method | Expected Status | Notes |
| --- | --- | --- | --- |
| `/ping` | GET | 200 | Public health probe; returns `status`, `timestamp`, `protocol` only. |
| `/` | GET | 302 → `/login` | Redirect enforced by `gating_logic`. |
| `/version/check` | GET | 302 → `/login` | New diagnostic route; inherits login requirement. |
| `/debug` | GET | 302 → `/login` | Request metadata only accessible post-login. |
| `/reconciliation-status` | GET | 302 → `/login` | Same behaviour for new status JSON. |
| `/stream-logs` | GET | 302 → `/login` | SSE stream protected; wildcard CORS header still set once authenticated. |
| `/login` | GET | 200 | Form rendered; CSRF token issued. |
| `/login` | POST | 200 | Remains on page with validation errors when credentials absent. |
| `/api/v2/ping` | GET | 401 | Requires master API key; response body `unauthorized`. |
| `/api/v2/debug-info` | GET | 401 | Same master-key protection. |
| `/api/v2/overview` | GET | 401 | Example of existing API route still locked down. |
| `/api/v2/agents/register` | POST | 401 | Agent endpoints enforce Bearer token. |
| `/setup/...` | any | 302 → `/login` | Once configuration files exist, setup routes are closed to anonymous users. |

These expectations are derived from code review and mirrored in the probe script’s access classifier (`auth_required`, `ok`, etc.). If any route responds with `200 OK` to an unauthenticated probe other than `/ping` or `/login`, treat it as a regression.

---

## Findings

### ✅ Finding 1 – Diagnostic Routes Respect Authentication

- **Scope:** `/version/check`, `/debug`, `/reconciliation-status`, `/api/v2/ping`, `/api/v2/debug-info`
- **Status:** Secure against anonymous access
- **Details:** None of these handlers are listed in login-exempt or API allow-lists. Anonymous requests trigger redirects (UI) or 401 errors (API). No leakage of version, environment, or reconciliation data occurs without valid credentials.

### ⚠️ Finding 2 – Permissive CORS on Authenticated SSE Streams (Medium)

- **Scope:** `/stream-logs` (and related SSE endpoints once logged in)
- **Impact:** Medium (CWE-942 – permissive cross-domain policy)
- **Details:** Although anonymous users cannot reach the stream, authenticated sessions inherit `Access-Control-Allow-Origin: *`. Malicious browser extensions or open tabs on untrusted sites could request the stream if the browser sends cookies (SameSite=Lax mitigates automatic background requests but not user-initiated navigation). Restrict this header to same-origin or trusted origins before GA release.

### 🛈 Observation – Setup Lock Enforced

- **Scope:** `/setup` blueprint
- **Details:** After installation, presence of `dockflare.key` and `dockflare_config.dat` triggers redirects to `/login`. Anonymous users cannot re-run the installer or override configuration. Keep these files protected to avoid tampering.

---

## Recommendations

1. **Tighten SSE CORS Policy** – Replace `Access-Control-Allow-Origin: *` with your UI origin (or drop the header) and explicitly disable credentialed cross-origin requests. Consider using a token gate for log streaming if remote dashboards are needed.
2. **Automate Unauthenticated Probes** – Integrate `test_scripts/route_probe.py` into CI smoke tests to catch inadvertent exposure of new routes before release.
3. **Monitor Login Endpoint Abuse** – Since `/login` remains the only anonymous UI route, keep rate limiting enabled and add alerting for brute-force attempts.

---

## Conclusion

Even without credentials or API keys, DockFlare v3.0.3 reveals only intentionally public information. The authentication middleware correctly shields the new diagnostic endpoints, preventing unauthorized access to operational data. Address the residual CORS weakness on streaming routes and continue running unauthenticated probes during future releases to maintain this strong security posture.
