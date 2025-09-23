# Welcome to the DockFlare Documentation!

DockFlare is a powerful, self-hosted ingress controller that simplifies Cloudflare Tunnel and Zero Trust management. It uses Docker labels for automated configuration while providing a robust web UI for manual service definitions and policy overrides.

This documentation provides comprehensive information for DockFlare. Whether you're a new user or an experienced one, you'll find everything you need to know to get the most out of DockFlare.

## Table of Contents

*   **[Home](Home.md)**
*   **Getting Started**
    *   [Prerequisites](Prerequisites.md)
    *   [Quick Start (Docker Compose)](Quick-Start-Docker-Compose.md)
    *   [Accessing the Web UI](Accessing-the-Web-UI.md)
*   **Core Concepts**
    *   [How DockFlare Works](How-DockFlare-Works.md)
    *   [DockFlare Agent & Multi-Server Architecture](Multi-Server-Agent.md)
    *   [Access Policy Best Practices](Access-Policy-Best-Practices.md)
    *   [Internal vs External `cloudflared`](Internal-vs-External-cloudflared.md)
    *   [State-Persistence](State-Persistence.md)
*   **Configuration**
    *   [Container Labels](Container-Labels.md)
*   **Usage Guide**
    *   [Basic Usage (Single Domain)](Basic-Usage-Single-Domain.md)
    *   [Using Multiple Domains (Indexed Labels)](Using-Multiple-Domains-Indexed-Labels.md)
    *   [Using Wildcard Domains](Using-Wildcard-Domains.md)
    *   [Managing DNS Zones](Managing-DNS-Zones.md)
    *   [Understanding Graceful Deletion](Understanding-Graceful-Deletion.md)
    *   [Using the Web UI](Using-the-Web-UI.md)
    *   [Backup & Restore](Backup-and-Restore.md)
*   **Advanced Topics**
    *   [External `cloudflared` Mode](External-cloudflared-Mode.md)
    *   [Switching Between Modes](Switching-Between-Modes.md)
    *   [Monitoring with Prometheus & Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    *   [Performance Tuning](Performance-Tuning.md)
    *   [Content Security Policy (CSP)](Content-Security-Policy.md)
    *   [Security Architecture & Hardening](Security-Architecture.md)
*   **Troubleshooting**
    *   [Common Issues](Common-Issues.md)
    *   [Debugging & Logs](Debugging-&-Logs.md)
    *   [Health Checks](Health-Checks.md)
*   **[Contributing](Contributing.md)**
*   **[License](License.md)**
