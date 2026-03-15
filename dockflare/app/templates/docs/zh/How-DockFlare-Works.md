# DockFlare 的工作原理

DockFlare 充当 Docker 环境与 Cloudflare 网络之间的桥梁，自动化完成将服务安全暴露到互联网的过程。它会持续监控您的 Docker 主机，并通过 Cloudflare API 代您管理隧道、DNS 记录和 Access 策略。

## 核心工作流程

核心流程大致可以分为以下几个步骤：

1. **监控 Docker 事件**：DockFlare 会监听 Docker socket 事件，例如容器的 `start` 和 `stop`。

2. **检测标签**：当新容器启动时，DockFlare 会检查其 `dockflare.` 标签。如果容器带有 `dockflare.enable=true`，DockFlare 就会将其纳入管理。

3. **调用 Cloudflare API**：根据这些标签，DockFlare 会在 Cloudflare 中配置所需资源：
   * **Cloudflare Tunnel**：在指定的 Cloudflare Tunnel 中添加一条入口规则，将公网主机名指向容器的内部网络地址，例如 `http://my-app:8080`。
   * **DNS 管理**：在 Cloudflare DNS 区域中创建 CNAME 记录，将您期望的公网主机名（例如 `my-app.example.com`）指向该 Cloudflare Tunnel。
   * **Access 策略**：如果您定义了访问控制标签，DockFlare 会创建或更新可复用的 Cloudflare Access 策略，通过 Zero Trust 规则保护您的服务，例如要求使用身份提供商登录，或者应用公共 `bypass`。

4. **自动清理**：当受管容器停止或被删除时，DockFlare 会自动执行清理流程。它会从 Cloudflare Tunnel 中删除对应的入口规则；如果没有其他服务继续使用该主机名，还会删除相应的 DNS 记录和 Access 应用。这样可以避免残留配置，让 Cloudflare 侧保持整洁。

## 组件概览

| 组件 | 职责 |
| --- | --- |
| DockFlare 主控端 | 托管管理界面和 API、监控 Docker 事件，并编排 Cloudflare 隧道、DNS 和 Access 策略。它以无 root 方式运行，并且只通过 socket proxy 与 Docker 通信。 |
| Docker Socket Proxy | `tecnativa/docker-socket-proxy` sidecar，向主控端暴露最小范围的 Docker API（`containers`、`events` 等），避免主控端直接挂载原始 Docker 套接字。 |
| Redis | 用于缓存、队列、日志流以及代理心跳和回传通道。它运行在私有的 `dockflare-internal` 网络中。 |
| DockFlare 代理端（可选） | 远程代理进程，在其他主机上复现主控端的行为，将 Docker 事件流式传回，并管理自己的 `cloudflared`。 |
| `cloudflared` | 维护主控端或各个代理到 Cloudflare 的隧道连接。 |

## 分层配置模型

DockFlare 采用灵活的分层配置方式，兼顾自动化与细粒度控制：

1. **Docker 标签（基础层）**：这是主要的自动化方式。您可以直接在 `docker-compose.yml` 或 `docker run` 命令中定义服务的完整配置，包括 hostname、内部服务 URL 和访问策略。这些标签就是自动化服务的事实来源。

2. **访问组（抽象层）**：为了避免在多个服务中重复定义复杂的访问策略，您可以在管理界面中创建可复用的**访问组**。这些模板会打包一组访问规则，例如允许公司邮箱登录或允许某些国家访问，并同步为命名的 Cloudflare Access 可复用策略。弹窗中的“公开 / 需身份验证”切换决定 DockFlare 最终生成 `bypass` 还是 `allow`。之后，您只需要通过单个标签，例如 `dockflare.access.group=my-policy-group`，就能把整套策略应用到容器上。

3. **界面覆盖（控制层）**：管理界面提供最高级别的控制。您可以：
   * **覆盖**任意服务的访问策略，无论它原本是由标签还是访问组定义的。这些覆盖是持久的，不会因容器重启而丢失。
   * **为非 Docker 服务创建手动入口规则**，例如为局域网中另一台机器上的服务创建入口。
   * **恢复**服务配置到 Docker 标签定义的状态，并丢弃界面中做出的覆盖。

这种分层模型让您可以对大多数服务做到“配置好就基本不用再管”，同时仍保留通过管理界面处理例外情况和复杂场景的能力。

---

## Access 策略架构（v3.0.3+）

### 可复用策略系统

DockFlare 现在使用符合 Cloudflare 最佳实践的 **可复用策略架构**：

1. **访问组** → 同步到 → **Cloudflare 可复用策略**
2. **Access 应用** → 引用 → **可复用策略 ID**
3. **单一事实来源** → 在一个地方更新，所有地方同时生效

这种架构消除了策略重复，并允许您在 DockFlare 或 Cloudflare 仪表板之间进行双向同步管理。

### 系统管理策略

DockFlare 会自动维护两个核心策略，以确保行为一致：

- **`public-default-bypass`**：公共访问 bypass 策略
  - 不可删除的系统策略
  - 在初始化期间自动创建
  - Cloudflare 名称：`DockFlare-Default-Public-Access-Bypass`
  - 决策：`bypass`，附带 `everyone` 规则
  - 用于所有需要公共访问且绕过区域保护的服务
  - 可避免在 Cloudflare 仪表板中出现重复的 bypass 策略

- **`authenticated-default`**：默认认证策略
  - 不可删除的系统策略
  - 在初始化期间自动创建
  - Cloudflare 名称：`DockFlare-Default-Authenticated-Access`
  - 决策：`allow`，并附带一次性 PIN 和邮箱限制
  - 用于基础的认证访问场景

### 旧标签迁移

DockFlare 会自动将旧标签迁移到系统策略：

- `dockflare.access.policy=bypass` → 使用 `public-default-bypass`
- `dockflare.access.group=bypass` → 使用 `public-default-bypass`
- `dockflare.access.policy=authenticate` → 使用 `authenticated-default`

迁移过程会在容器处理和协调时自动完成，无需人工干预。

### 区域默认策略

区域级 wildcard 策略（`*.domain.com`）通过优先级提供分层安全性：

1. **特定 hostname 策略**（例如 `app.example.com`）- 最高优先级
2. **区域 wildcard 策略**（例如 `*.example.com`）- 后备保护
3. **无策略** = 公共访问，不使用 Access App - 默认行为

这意味着即使服务被遗忘或没有文档记录，也仍然会受到区域级策略的保护，相当于额外的安全兜底。

**示例：**
- 区域策略：`*.internal.company.com` → 要求使用公司邮箱进行身份验证
- 特定服务：`public-demo.internal.company.com` → 使用 `public-default-bypass`
- 被遗忘的服务：`test.internal.company.com` → 仍受区域策略保护并要求认证
