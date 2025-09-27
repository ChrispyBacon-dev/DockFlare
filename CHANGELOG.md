# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v3.0.1] (Hotfixes) - 2025-09-27

### Fixed
- **IP Whitelist Access Policies:** Corrected an issue where IP-based access policies were not working as expected. DockFlare now correctly creates a `bypass` rule for IP whitelists and a separate `allow` rule for email-based authentication, ensuring whitelisted IPs can access services without an additional authentication step.
- **Access Policy Updates:** Fixed a bug where updating an existing ingress rule's Access Policy would fail with an "application already exists" error. DockFlare now correctly updates the existing Cloudflare Access application instead of trying to create a new one.
- **API Error Logging:** Reduced the severity of the log message for a `403 Forbidden` error when fetching a user's email. This is an expected and non-critical error when using a scoped API token.
(raised by @durzo issue tracker #216 #217)

---
## [v3.0.1] - 2025-09-26

### Added
- **OAuth/OIDC Login Support:** Added support for external authentication providers like Google and Authentik via a new, generic OpenID Connect system.
- **OAuth Documentation:** Created a new help document for setting up OAuth providers.

### Changed
- **Redesigned Login Page:** The login page has been updated with a modern design, provider logos, and a unified flow for both password and OAuth logins.
- **Improved Usability:** The settings page now displays the required Callback URL for OAuth providers, and DockFlare can discover its public hostname from Docker labels.
- 
### Security
- **Login Rate Limiting:** Implemented rate limiting on the password login form (6 attempts per minute) to protect against brute-force attacks.

---
## [v3.0.0] - 2025-09-25

### Fixed (Hotfixes)

#### **Agent Container Label Processing**
- **Fixed access policy parsing** for Agent containers - containers with `dockflare.access.policy=authenticate` now display correct policy instead of "None (Public)"
- **Added support for all documented labels** in Agent processing including `dockflare.no_tls_verify`, `dockflare.originsrvname`, `dockflare.httpHostHeader`
- **Implemented indexed labels support** for Agent containers (e.g., `dockflare.0.hostname`, `dockflare.1.service`) for multiple domain configurations
- **Enhanced backwards compatibility** - Agent containers now fully support legacy `cloudflare.tunnel.*` label formats

#### **Migration Logic Improvements**
- **Fixed tunnel migration analysis** - containers with legacy `cloudflare.tunnel.*` labels are now properly recognized during migration instead of showing as "orphaned"
- **Enhanced migration service compatibility** with backwards compatible label checking across all migration functions
- **Improved container matching logic** for more accurate auto-import and conflict detection

#### **Redis Database Configuration Enhancement**
- **Added `REDIS_DB_INDEX` environment variable** - allows specifying Redis database index (0-15) for better isolation when sharing Redis across multiple Docker containers
- **Enhanced Redis URL parsing** - dynamically constructs Redis connection URL with specified database index
- **Maintains full backward compatibility** - existing docker-compose files continue to work without changes, defaults to database 0

#### **Dependencies Security Update**
- **Updated Redis client** from 4.5.1 to 4.5.5 to address security vulnerabilities (CVE-2023-28859, CVE-2023-28858)

---
## [v3.0.0] - 2025-09-23

### Added

#### **Multi-Host Management with DockFlare Agent (Beta)**
- **Lightweight agent deployment** on remote Docker hosts with secure API key authentication
- **Secure registration and enrollment** process via master UI with encrypted agent key store
- **Command polling architecture** with configurable intervals and Redis-backed queues
- **Real-time heartbeat monitoring** with 30-second intervals and automatic timeout detection
- **Automatic tunnel configuration** and container discovery on remote hosts
- **Migration assistant** for importing existing tunnel rules and resolving conflicts
- **Agent repository**: [DockFlare-Agent-prd](https://github.com/ChrispyBacon-dev/DockFlare-Agent-prd)

#### **Centralized Agents Management UI**
- **Professional agent dashboard** with API key generation and management
- **Real-time LED status strips** for visual heartbeat monitoring (replaces text-based timestamps)
  - 15-dot LED strips with 2-second resolution showing 30-second heartbeat window
  - Color-coded states: Green (healthy), Yellow (warning), Red (critical), Grey (offline)
  - Animated LED extinguishing as heartbeat window expires
- **Shortened Agent IDs** (8 characters + hover tooltip) for better readability
- **Dropdown action menus** for cleaner interface (enroll, rename, migrate, redeploy, remove)
- **Agent enrollment** with existing or new tunnel assignment
- **Bulk agent operations** and tunnel reassignment capabilities
- **Migration conflict resolution** interface for handling rule conflicts

#### **Redis-Powered Architecture**
- **Redis requirement** for caching, command queues, and event bus
- **Agent heartbeat storage** and real-time monitoring
- **Command/event distribution** system for multi-host coordination
- **Foundation for future horizontal scaling** and performance improvements

#### **Enhanced Security Framework**
- **Non-root container execution** (runs as user 65532:65532) with init container for permissions
- **Master API key reveal-on-demand** with CSRF protection and secure token handling
- **Encrypted agent key store** with secure credential management and rotation
- **Locked-down setup wizard** with restore-from-backup option
- **Docker socket proxy integration** (tecnativa/docker-socket-proxy) for reduced attack surface

#### **Comprehensive Backup & Restore System**
- **Complete instance backup** including encrypted credentials and agent keys
- **Timestamped backup archives** with full configuration preservation (.zip format)
- **UI-based restore functionality** for disaster recovery scenarios
- **Setup wizard integration** for fresh installations with backup import

#### **Remote Manual Rules Management**
- **Create manual ingress rules** from master UI for any enrolled agent
- **Apply rules to any enrolled tunnel** regardless of host location
- **Cross-host tunnel management** capabilities with centralized control

#### **Improved Tunnel Management**
- **"All Cloudflare Tunnels on Account" panel** with one-click delete functionality
- **Simplified stale tunnel cleanup** process across multiple hosts
- **Enhanced tunnel status monitoring** with real-time updates

#### **Automatic Zone Detection**
- **Intelligent Cloudflare zone detection** from hostname labels
- **Fallback to default zone** when detection fails
- **Improved service discovery** for label-driven configurations

#### **Documentation Overhaul**
- **New Quick Start Guide** for Docker Compose v3 setup with Redis
- **Comprehensive Multi-Server & Agent** deployment guide
- **Security Architecture** documentation with threat model
- **Backup & Restore** operational guide with best practices
- **Updated API documentation** for agent integration

### Changed

#### **Breaking Changes**
- **Redis is now required** - DockFlare will not start without `REDIS_URL` environment variable
- **New `docker-compose.yml` structure** with Redis, socket proxy, init container, and volume changes
- **Embedded cloudflared limited** to master host only (remote hosts use DockFlare Agent)

#### **UI/UX Improvements**
- **Professional LED heartbeat indicators** replacing static text timestamps
- **Enhanced agent table layout** with improved usability and responsive design
- **Modernized dropdown interfaces** throughout the application
- **Streamlined action menus** with icon-based navigation

#### **Architecture Changes**
- **Master API key security** with reveal-on-demand modal instead of embedded display
- **Setup wizard hardening** with route locking after initial configuration
- **Docker socket proxy** integration for enhanced security posture

### Security

- **Hardened API endpoints** requiring master key for admin routes and agent API keys for polling
- **CSRF-protected key reveal** so master key is not embedded in UI source code
- **Encrypted agent credentials** with secure key rotation capabilities
- **Non-root container execution** significantly reducing attack surface
- **Socket proxy isolation** preventing direct Docker socket access

### Fixed

- **Improved error handling** for agent communication failures and network issues
- **Enhanced tunnel status detection** and reporting across multiple hosts
- **Better handling of disconnected agents** with automatic cleanup procedures
- **Cloudflare API reliability** improvements for multi-host scenarios

### Known Issues

- **Cloudflared version detection** currently shows hardcoded version (2025.9.0) while automatic detection is being fixed
- **DockFlare Agent is in beta** - performance with high-volume event streams may require tuning of `POLL_INTERVAL` settings
- **Redis is critical component** - monitor health in single-node setups as agent communication depends on it
- **Agent repository automated builds** coming soon for simplified deployment

### Migration Notes

#### **Upgrade Process**
1. **Create full backup** via Settings → Backup & Restore before upgrading
2. **Update docker-compose.yml** to v3 structure with Redis and socket proxy components
3. **Create external network**: `docker network create cloudflare-net`
4. **Pull new image** and restart: `docker compose up -d`
5. **Review Agents page** to begin multi-host enrollment process
6. **Deploy agents** on remote hosts using generated API keys from dashboard
7. **Use restore option** in setup wizard for fresh installations

#### **Technical Requirements**
- **Minimum Docker Compose version**: 3.8
- **Redis version**: 7-alpine (included in new compose stack)
- **Socket proxy**: tecnativa/docker-socket-proxy:v0.4.1
- **Container user**: 65532:65532 (non-root execution)
- **External network**: cloudflare-net (must be created manually)

#### **Agent Deployment**
- **Agent heartbeat interval**: 30 seconds (configurable via `HEARTBEAT_INTERVAL`)
- **LED status indicators**: 15-dot strips with 2-second resolution
- **Command polling**: configurable via `POLL_INTERVAL` (default: 5 seconds)
- **Automatic tunnel management**: full lifecycle from enrollment to cleanup

## [v2.1.7] - 2025-08-30

### New
- UI: Added a version check feature to the Settings page. This allows users to verify if their running DockFlare instance is up-to-date by comparing the local Docker image digest against the official repository or by checking the latest GitHub release tag.

### Changed
- UI: Reorganized the Settings page to include a left-side sticky navigation and section anchors for improved discoverability and faster navigation.
- UI: Added smooth scrolling and adjusted anchor offset so section headings are not hidden behind the sticky top header when navigating to anchors.
- UI: Left-nav links now resolve to the Settings route with fragment identifiers (e.g. /settings#general-settings) so anchors work from any page.
- UI: Added a small client-side script that highlights the active left-nav item while scrolling (IntersectionObserver with a fallback).
- Fix: Kept all existing form names, IDs and POST endpoints unchanged to avoid breaking backend functionality.

## [v2.1.6] - 2025-08-24

### Security
- **Dependency Vulnerability:** Patched an outdated `brace-expansion` npm package (related to CVE concerning inefficient regex) by updating it to version 2.0.2.
- **Path Injection:** Hardened the `/help/<path:page>` route against path traversal attacks by implementing stricter validation using `os.path.abspath`.
- **Open Redirect:** Secured the login redirect mechanism by validating the `next` parameter to prevent redirection to external, malicious sites.
- **Information Exposure:** Prevented the leakage of sensitive exception details and stack traces in API/JSON responses across multiple endpoints (`/cloudflare-ping`, `/debug`, `/api/v2/debug-info`).
- **Insecure CI/CD Workflow:** Restricted permissions in the GitHub Actions workflow to `contents: read` to adhere to the principle of least privilege.

## [v2.1.5] - 2025-08-24

### New
- **Help Documentation:** Added a comprehensive help section to the web UI, providing users with easy access to documentation and guides.

### Fixed
- **Country Dropdown Menu:** Fixed an issue where the country dropdown menu in the Access Group modal was limited to 50 entries.
- **UI Refinements:** Made various minor refinements to the web UI for improved usability and a more polished user experience.

## [v2.1.4] - 2025-08-23

### New
- **Geo-Fencing Support:** Access Groups now support country-based blocking, allowing you to easily block traffic from specific countries (thanks @psybernoid, #183).
- **Multiple Policies per Rule:** You can now apply multiple Access Groups to a single ingress rule, both via Docker labels (`dockflare.access.groups`) and the web UI, to combine and layer policies (thanks @psybernoid, #183).

### Changed
- **UI/UX Refinement:** The Access Groups manager has been moved from the Settings page to its own dedicated "Access Policies" page in the main navigation bar for improved visibility and workflow.
- **IP-Based Access Policies:** Access Groups now fully support creating policies based on allowed IP ranges (CIDR notation), in addition to emails.


## [v2.1.3] - 2025-08-15

### New
- **Update Cloudflare Credentials:** Added a new section in the Settings page that allows users to update their Cloudflare Account ID and API Token directly from the UI.

## [v2.1.2] - 2025-08-14

### Changed
- **Unified Ingress Rule Editing:** The "Manage Policy" dropdown has been completely replaced by a unified editing modal. All rules (manual or from labels) can now be fully edited using the same comprehensive form.
- The table column for editing has been renamed from "Manage Policy" to "Manage Rule".
- The editing modal has been renamed from "Edit Manual Ingress Rule" to "Edit Ingress Rule".
- The redundant "Edit" button in the "Actions" column for manual rules has been removed to streamline the UI.
- When a rule from a container label is edited via the UI, it is now correctly marked with a "UI Override" flag, and the "Revert to Labels" functionality is preserved.

### Removed
- Removed the `ui_update_access_policy` backend route and associated frontend logic, as it was made obsolete by the new unified editing modal.

### New
- Added Favicon: The web UI now has a favicon, making it easier to spot in your browser tabs.

## [2.1.1] - 2025-08-12

### Added

*   **Revamped Setup Wizard:** The initial setup wizard has been re-sequenced for a more logical flow (User -> Cloudflare -> Tunnel -> Finalize).
*   **Setup Step Indicator:** A visual progress indicator has been added to all setup pages.
*   **Detailed Setup Explanations:** Added clear, descriptive text to each step and field in the setup process to improve user guidance.
*   **Disable Password Login:** Added a new option on the Settings page under "Security" to disable password-based login. This allows for public access to the dashboard, intended for use with an external authentication provider like Cloudflare Access.
*   **Cancel Migration Option:** Added a "Start Fresh" button to the `.env` migration screen, allowing you to cancel the migration and begin a manual setup.

### Fixed

*   Corrected the initial redirect for the setup process, which was pointing to a non-existent route.
*   Fixed a template error that caused a crash on the final step of the setup wizard.
*   Corrected the setup flow logic. When a user proceeds with a migration, they are now correctly taken to the final step after user creation, bypassing unnecessary manual configuration.
*   The "Disable Password Login" setting now persists correctly after restarting the DockFlare container.
*   Resolved a redirect loop (`ERR_TOO_MANY_REDIRECTS`) that occurred when password login was disabled.

### Changed

*   The `/ping` endpoint is now exempt from authentication to allow for Docker health checks.
*   The `/ping` endpoint now dynamically reports the application version via the config.APP_VERSION variable.
*   The "Change Password" form on the settings page is now hidden when password login is disabled.
*   The user creation page now provides clearer instructions depending on whether the user is in a migration or a fresh setup flow.
*   Updated the security warning text related to disabling password login for better clarity.

## [v2.1.0] - 2025-08-12

This release focuses on simplifying the initial setup, enhancing security with UI authentication, and improving overall usability.

### New

-   **Pre-Flight Setup Wizard:** A new browser-based setup wizard for first-time installations replaces the need for `.env` files. This guides users through configuring Cloudflare credentials and tunnel settings step-by-step.
-   **UI Authentication:** The DockFlare UI is now protected by a login page.
-   **Password Management:** Users can now change their UI password from a new "Security" section on the Settings page. A secure, manual process for password resets has been implemented.
-   **Post-Setup Configuration:** Core settings (Tunnel Name, Zone IDs, Rule Grace Period) can now be modified directly from the UI at any time.
-   **Seamless Migration:** An automatic migration process is in place for existing users to import settings from their `.env` file and create a new UI password.

### Changed

-   **Logout Button:** A logout button has been added to the main navigation bar.
-   **UI/UX:** The theme selector is now an icon-only button for a cleaner interface.

### Security

-   **Encrypted Configuration:** All sensitive credentials, including the Cloudflare API token and UI password, are now stored in a fully encrypted `dockflare_config.dat` file.

### Removed

-   **`.env` File Support:** DockFlare no longer uses `.env` files for configuration after the initial migration. All settings are managed through the UI and the encrypted configuration file.

## [v2.0.4] - 2025-08-12

This is a dedicated security hardening release that reintroduces security enhancements from a previously rolled-back version (v2.0.5). A special thanks to GitHub user **@bcurran3** and Reddit user **t2_hur2hqu6k** for their valuable feedback and for helping make DockFlare more secure.

### Security

-   **CSRF Protection:** All forms in the web UI are now protected with anti-CSRF tokens to prevent Cross-Site Request Forgery attacks.
-   **Strengthened Content Security Policy (CSP):** The CSP has been made more restrictive to mitigate the risk of Cross-Site Scripting (XSS) and other injection attacks.
-   **Pinned Dependencies:** All Python dependencies in `requirements.txt` are now pinned to specific versions to ensure build reliability and prevent potential supply-chain attacks.

## [v2.0.1] - 2025-08-05

This is a follow-up release to address several minor bugs found after the major v2.0 update. It also restores support for Bastion mode and introduces a new backup and restore feature.

### New

-   **Backup & Restore via UI:** A new "Backup & Restore" card has been added to the Settings page.
    -   You can now download a timestamped `state.json` backup directly from the UI.
    -   You can upload a `state.json` backup file to completely restore your DockFlare configuration. After a restore, DockFlare automatically reloads the state and triggers a reconciliation to bring your Cloudflare setup in sync.

### Added

-   **Bastion Mode for Browser SSH/VNC:** Re-introduced and fixed support for **Bastion Mode** (`bastion`) as a service type in the manual rule creation UI. This service type is used for Cloudflare's browser-rendered SSH and VNC. Unlike other service types, it does not require an internal service address to be specified in DockFlare; it enables a secure gateway at the public hostname, which you then connect to using the `cloudflared` client on your local machine.

### Fixed

-   **UI:** Fixed an issue where the DNS record toggle button (`+`) for tunnels on the Settings page was not functional after the UI reorganization.
-   **State Management:** Corrected a bug where the `access_group_id` for a rule was not being saved to or loaded from the `state.json` file. This caused the "Group:" display in the UI to be empty for Docker-managed rules after a restart.
-   **UI:** The "UI Override" badge and "Revert" button will no longer be displayed for manual rules, as they have no Docker labels to override or revert to.
-   **Validation:** Fixed a validation error that incorrectly rejected `bastion` as a valid service type, which prevented browser-based SSH/VNC rules from being created.

## [2.0.0] - 2025-08-01

### Added

-   **Access Groups:** Introduced a major new feature for centralized policy management. You can now create reusable policy templates (Access Groups) in the UI and apply them to any container or manual rule with a single `dockflare.access.group` label.
-   **New "Settings" Page:** Added a dedicated page in the UI to house configuration and infrastructure details, including the new Access Groups manager, the list of all Cloudflare Tunnels, and the agent status.
-   **Official Project Website:** Launched the official website at [https://dockflare.app](https://dockflare.app), which now serves as the central hub for documentation, guides, and project information.

### Changed

-   **UI Overhaul:** The user interface has been significantly reorganized for a better workflow.
    -   The main page is now a focused **Dashboard** displaying only Managed Ingress Rules and Real-time Logs.
    -   A new top navigation bar has been added for easy switching between the Dashboard and Settings.
    -   "Add" and "Edit Manual Rule" modals now integrate seamlessly with Access Groups, allowing you to assign a group from a dropdown menu.
-   **Backend Policy Management:** The entire backend logic for handling labels and access policies has been refactored to support the new Access Groups system.
-   **UI Polish:**
    -   The logo in the header has been moved to the left, mirroring the layout of the new project website.
    -   Modals with a large amount of content will now scroll correctly.

### Fixed

-   **Centralized Versioning:** The project version number is now managed from a single source to prevent inconsistencies across the UI.

## [1.9.5] - 2025-07-27

### Fixed
- **Agent Container Startup Resilience:** Resolved a critical issue where the managed `cloudflared` agent container would fail to start if its associated Docker network was removed and recreated. The startup logic in `tunnel_manager.py` now intelligently detects this "stale network" error, automatically removes the broken agent container, and creates a new one, significantly improving reliability in dynamic Docker environments.

## [1.9.4] - 2025-07-19

### Fixed
- **Auto-Redirect for Identity Providers:** Resolved a regression from v1.9.0 where using the `access.auto_redirect_to_identity=true` label along with `access.allowed_idps` would result in a Cloudflare API error. The `access_manager.py` module has been corrected to include the required top-level `allowed_idps` field in the API payload, restoring the auto-redirect functionality for label-based rules.

## [1.9.3] - 2025-07-19

### Fixed
- **Critical UI Fix for Access Policies:** Resolved a critical bug causing an 'Internal Server Error' when creating or editing manual rules, or updating a Docker-managed rule's policy, to use the 'Authenticate by Email' method via the web UI. This was a regression caused by recent updates to the Cloudflare Access API handling in `access_manager.py` which were not reflected in the UI routes. The routes in `app/web/routes.py` have been updated to correctly construct the Access Policy payload, resolving the `TypeError` and API validation errors.

## [1.9.2] - 2025-06-25

### Added
- **HTTP Host Header Support:** Implemented support for the new `dockflare.httpHostHeader` Docker label, allowing users to override the `Host` header sent to their origin service. This feature is also fully supported for manual ingress rules via the web UI (Add/Edit modals and display in the Managed Rules table). Applies only to HTTP/HTTPS services.

### Fixed
- **Service Validation for Docker Names:** Corrected the `is_valid_service` regex to properly allow underscores (`_`) in service hostnames (e.g., `http://my_app:80`), accommodating common Docker service naming conventions.

### Changed
- **Optional Ports for HTTP/HTTPS Services:** Modified `is_valid_service` to make the port optional for `http://` and `https://` service targets (e.g., `http://my-service` is now valid). Default ports (80 for HTTP, 443 for HTTPS) will be implicitly used by Cloudflare Tunnel if no port is specified.

## [1.9.1] - 2025-06-23

### Added
- **Prometheus Metrics Endpoint:** Added support for enabling the Prometheus metrics endpoint on the managed `cloudflared` agent via the new `CLOUDFLARED_METRICS_PORT` environment variable. The agent container will be automatically reconciled if this setting is added, changed, or removed.

## [1.9.0] - 2025-06-23

### Fixed
- **Automatic Rule Cleanup for Multi-Path Services:** Resolved a critical bug where the background cleanup task failed to process and delete expired rules for multi-path services.
- **`allowed_idps` Label Functionality:** Resolved a bug that caused Cloudflare API errors when using the `access.allowed_idps` label. DockFlare now correctly constructs Access Policy rules using the modern `login_method` keyword.
- **UI Policy Management for Multi-Path Rules:** Corrected an issue where managing Access Policies from the web UI would fail for rules that included a path.
- **Manual Rule Creation:** Fixed a bug preventing manually created rules from being correctly added to the Cloudflare Tunnel configuration.
- **UI Efficiency:** Policy updates from the UI now prevent unnecessary API calls if the configuration hasn't changed.

### Changed
- **Rewritten Rule Cleanup Logic:** The background cleanup task has been completely rewritten to be resource-aware. It now intelligently checks if a shared resource (like a DNS record or Access Application) is still in use by other active rules before deleting it. This ensures correct and stable behavior when managing complex, multi-path services.
- **Improved Cleanup Responsiveness:** The default value for `CLEANUP_INTERVAL_SECONDS` has been reduced from 300 to **60 seconds**, making the automatic deletion of expired rules more responsive and intuitive.

## [1.8.9] - 2025-06-22

### Added
- **Agent Container Reconciliation:** DockFlare now intelligently checks the managed `cloudflared-agent` container on startup. If it detects a configuration mismatch (e.g., wrong network or image version) compared to the `.env` file, it will automatically recreate the agent with the correct settings.

### Changed
- **Startup Logic:** Refactored the main application startup sequence to unconditionally trigger the new agent reconciliation logic, ensuring configuration changes from the `.env` file are always applied.

### Fixed
- **UI Policy Management for Multi-Path Rules:** Corrected an issue where managing Access Policies from the web UI would fail for rules that included a path. The UI now correctly parses the hostname and path, allowing for reliable policy updates.
- **Manual Rule Creation:** Fixed a bug where manually created rules from the UI were not being correctly added to the Cloudflare Tunnel's ingress configuration.
- **UI Efficiency:** Policy updates from the UI now check if the requested configuration already matches the live Cloudflare configuration, preventing unnecessary API calls.

## [1.8.7] - 2025-06-10

### Fixed
- **Critical Agent Startup Fix:** Resolved a bug where the managed `cloudflared` agent failed to start due to a `Provided Tunnel token is not valid` error. The token parsing logic is now more robust, handling both new JSON and legacy raw text responses from the Cloudflare API.

## [1.8.6] - 2025-06-07

### Added
- **Edit Manual Rule Functionality:** A new "Edit" button and modal now allow for direct editing of existing manual ingress rules via the web UI.
- **Intelligent Resource Management:** The backend logic for editing rules now cleanly removes old, unused Cloudflare resources (DNS records, Access Applications) and creates/updates new ones as needed.

### Changed
- **UI Code Reusability:** Refactored UI JavaScript to create a shared helper function for path input logic, reducing code duplication between the "Add" and "Edit" modals.

## [1.8.5] - 2025-05-29

### Added
- **Origin Server Name (SNI) Support:** Added support for specifying `originServerName` for an ingress rule via the `...originsrvname` Docker label and a new field in the Manual Rule UI, allowing for more granular control over TLS connections to origin services.

## [1.8.4] - 2025-05-28

### Added
- **Path-Based Routing:** Introduced the ability to define specific URL paths for ingress rules via Docker labels (`...path=/...`) and the Manual Rule UI.
- **Extended Service Type Support:** Added robust support for `tcp`, `ssh`, `rdp`, and `http_status` service types in addition to HTTP/S.
- **Direct Access Policy on Manual Rules:** The "Add Manual Rule" UI now allows for direct assignment of an Access Policy upon creation.

### Changed
- **UI/UX:** The "Add Manual Rule" modal was restructured for improved clarity, and links in the main table now correctly include the path.
- **Validation:** Implemented stricter validation for service URL formats to ensure proper configuration.

## [1.8.0] - 2025-05-27

### Changed
- **Major Codebase Refactor:** The application was restructured into a modular, package-based architecture (`app/core/`, `app/web/`) to improve maintainability and separation of concerns.
- **Externalized JavaScript:** All inline JavaScript was moved from HTML templates to a dedicated `app/static/js/main.js` file.
- **Enhanced Logging:** Added more detailed logging, including object ID tracking during critical state operations, to aid in debugging.

### Fixed
- **Threading and State Issues:** Resolved several bugs discovered during the refactor, including potential circular imports, state-saving race conditions (by implementing `threading.RLock`), and various `NameError`, `TypeError`, and `AttributeError` exceptions.

## [1.7.1] - 2025-05-22

### Fixed
- **Multi-Zone DNS Scanning:** Corrected an issue where the "All Cloudflare Tunnels on Account" view only scanned for DNS records in the primary `CF_ZONE_ID`, and now correctly respects the `TUNNEL_DNS_SCAN_ZONE_NAMES` setting.

## [1.7.0] - 2025-05-17

### Added
- **Manual Ingress Rule Management:** Introduced the ability to add, manage, and delete ingress rules for non-Docker services directly from the web UI.

### Changed
- **Authoritative Ingress Management:** The tunnel update logic now takes an authoritative stance, ensuring the Cloudflare configuration perfectly matches DockFlare's managed state by removing stale, non-DockFlare rules.
- **UI/UX:** Improved readability of status badges and localized the "Expires At" timestamp to the user's browser timezone.

### Fixed
- **Ingress Rule Deletion:** Resolved a critical bug where deleting a rule would not correctly remove the corresponding ingress rule from the Cloudflare Tunnel configuration.

## [1.6.0] - 2025-05-15

### Added
- **UI-Driven Access Policy Management:** Users can now override label-defined Access Policies directly from the web interface.
- **Persistent UI Overrides:** UI-driven policy changes are saved to `state.json` and persist across restarts.
- **"Revert to Labels" Functionality:** A new button allows users to easily revert a service's policy back to be controlled by its Docker labels.

### Changed
- **Major UI Refresh:** The entire web UI was overhauled using the DaisyUI component library for a cleaner, modern, and themeable interface.
- **Theme Selector:** Added a UI theme selector with numerous built-in themes.

## [1.4.0] - 2025-05-10

### Added
- **Account-Wide Tunnel Listing:** A new table on the status page displays all Cloudflare Tunnels on the configured account, providing a centralized overview for multi-host deployments.
- **Integrated DNS Record Viewer:** Added the ability to dynamically fetch and display all CNAME DNS records pointing to any tunnel on the account, directly from the UI.

## [1.0.0] - 2025-04-12

### Added
- **Initial Release:** Core functionality of DockFlare, providing dynamic Cloudflare Tunnel configuration based on Docker container labels.
