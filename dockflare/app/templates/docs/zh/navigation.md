# 欢迎来到 DockFlare 文档

DockFlare 是一款功能强大的自托管入口控制器，可简化 Cloudflare Tunnel 与 Zero Trust 的管理。它通过 Docker 标签实现自动化配置，同时提供网页管理界面，用于手动定义服务与覆盖策略。

本文档涵盖 DockFlare 的核心概念、配置方式与常见运维场景。无论您是首次上手还是已在生产环境中使用，都能在这里快速找到所需信息。

## 目录

* **[主页](Home.md)**
* **开始使用**
    * [先决条件](Prerequisites.md)
    * [快速入门 (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [访问网页管理界面](Accessing-the-Web-UI.md)
* **核心概念**
    * [DockFlare 的工作原理](How-DockFlare-Works.md)
    * [DockFlare 代理与多服务器架构](Multi-Server-Agent.md)
    * [访问策略最佳实践](Access-Policy-Best-Practices.md)
    * [区域默认策略](Zone-Default-Policies.md)
    * [内部与外部 `cloudflared`](Internal-vs-External-cloudflared.md)
    * [状态持久化](State-Persistence.md)
* **配置**
    * [容器标签](Container-Labels.md)
    * [身份提供商](Identity-Providers.md)
    * [OAuth 提供程序设置](OAuth-Provider-Setup.md)
* **使用指南**
    * [基本用法（单域）](Basic-Usage-Single-Domain.md)
    * [使用多个域（索引标签）](Using-Multiple-Domains-Indexed-Labels.md)
    * [使用通配符域名](Using-Wildcard-Domains.md)
    * [管理 DNS 区域](Managing-DNS-Zones.md)
    * [了解优雅删除](Understanding-Graceful-Deletion.md)
    * [使用网页管理界面](Using-the-Web-UI.md)
    * [备份与恢复](Backup-and-Restore.md)
* **高级主题**
    * [外部 `cloudflared` 模式](External-cloudflared-Mode.md)
    * [模式切换](Switching-Between-Modes.md)
    * [使用 Prometheus 和 Grafana 进行监控](Monitoring-with-Prometheus-&-Grafana.md)
    * [性能调整](Performance-Tuning.md)
    * [内容安全策略 (CSP)](Content-Security-Policy.md)
    * [安全架构与强化](Security-Architecture.md)
* **故障排除**
    * [常见问题](Common-Issues.md)
    * [调试和日志](Debugging-&-Logs.md)
    * [健康检查](Health-Checks.md)
    * [CLI 实用程序](CLI-Utilities.md)
* **[贡献](Contributing.md)**
* **[许可证](License.md)**
