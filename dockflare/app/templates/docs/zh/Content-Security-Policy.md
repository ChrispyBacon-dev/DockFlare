# 内容安全策略 (CSP)

## 什么是内容安全策略？

内容安全策略 (CSP) 是一种 Web 安全标准，有助于防止某些类型的攻击，尤其是跨站点脚本 (XSS) 和数据注入攻击。它的工作原理是告诉浏览器哪些内容源（脚本、样式、图像等）是可信的并允许在网页上加载。

## DockFlare 的 CSP

DockFlare 应用程序本身有一个 Web 界面。为了保护这个界面并确保其安全，DockFlare 在自己的 UI 上实施了严格的内容安全策略。

这是一项重要的内部安全功能，旨在保护您（管理员）在使用 DockFlare 仪表板时免受潜在的基于浏览器的漏洞的影响。

## CSP 的范围

重要的是要了解 DockFlare 的 CSP **仅适用于 DockFlare Web UI 本身**。

它**不会**影响、修改或添加任何 CSP 标头到通过 Cloudflare 隧道代理到您自己的应用程序的流量。如果您想在自己的应用程序上实现 CSP，则必须在应用程序本身内进行配置（例如，通过在 Web 服务器或应用程序代码中设置 `Content-Security-Policy` HTTP 标头）。

## 配置

DockFlare 的 CSP 是其安全态势不可或缺的一部分，并且**用户不可配置**。该策略经过精心设计，尽可能具有限制性，同时仍允许 UI 正常运行。

如果您有兴趣了解有关内容安全策略一般如何工作的更多信息，[关于 CSP 的 MDN Web 文档](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) 是一个极好的资源。