# 内容安全策略（CSP）

## 什么是内容安全策略？

内容安全策略（CSP）是一种 Web 安全标准，用来限制页面可以加载哪些脚本、样式、图片等资源，从而降低跨站脚本（XSS）和数据注入等攻击风险。

## DockFlare 的 CSP

DockFlare 自带网页管理界面。为了保护这套界面，DockFlare 为其自身页面启用了严格的内容安全策略。

这是 DockFlare 的一项内部安全机制，用来降低您在使用管理界面时遭遇浏览器侧漏洞的风险。

## CSP 的范围

需要注意的是，DockFlare 的 CSP **只作用于 DockFlare 自己的网页界面**。

它**不会**影响、修改或额外添加任何 CSP 响应头到通过 Cloudflare 隧道转发到您自己应用的流量中。如果您希望自己的应用也启用 CSP，需要在应用本身或其 Web 服务器中配置，例如设置 `Content-Security-Policy` HTTP 响应头。

## 配置

DockFlare 的 CSP 是其整体安全设计的一部分，**不能由用户自定义**。这套策略已经尽量在保证界面正常工作的前提下做到了更严格的限制。

如果您想进一步了解 CSP 的工作方式，可以参考 [MDN 的 CSP 文档](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)。
