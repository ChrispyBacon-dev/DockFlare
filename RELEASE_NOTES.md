# Release v3.0.6

## 🚀 Improvements & Fixes

### ⚡ Docker Event Listener Efficiency
Significantly reduced log spam and improved resource utilization by implementing filtered Docker event listeners. DockFlare now only processes container events (start/stop) for containers explicitly opted-in via `dockflare.enable` or the legacy `cloudflare.tunnel.enable` labels, preventing unnecessary inspection of unmanaged containers. (Fixes #296)

### 🏷️ Access Policy Label Rename
Renamed the Access Policy label "None (Public - No App)" to "No Policy Assigned" in the Dashboard. This change accurately reflects that while no specific policy is assigned to the rule, the service might still be protected by a broader Zone Policy, removing the misleading "Public" designation.
