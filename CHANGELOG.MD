# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---
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