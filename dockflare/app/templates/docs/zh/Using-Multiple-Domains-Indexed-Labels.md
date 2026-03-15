# 使用多个域（索引标签）

DockFlare 提供了一个名为 **索引标签** 的强大功能，允许您为单个容器定义多个独立的入口规则。当您想要在不同的公共主机名上公开同一服务的不同端口或路径时，这特别有用。

## 它是如何工作的

要创建多个规则，您只需在标准 DockFlare 标签上添加一个整数和一个点作为前缀，从 `0` 开始。例如，`dockflare.0.hostname`、`dockflare.1.hostname` 等。

* 每个索引（例如，`0`、`1`、`2`）代表一个单独的入口规则。
* 启动新规则始终需要索引主机名（例如 `dockflare.<index>.hostname`）。
* 同一索引处的其他标签（例如 `dockflare.<index>.service`）将仅适用于该特定规则。

## 后备机制

索引标签的一个关键特性是后备机制。如果您没有为规则提供特定的索引标签，它将**回退到相应基本（非索引）标签的值**。

这允许您在基本级别定义一次通用设置，并且仅覆盖需要为每个索引规则更改的特定值。

## 示例：公开 Web UI 和 API

假设您有一个容器，它既为端口 `80` 上的 Web 应用程序提供服务，又为端口 `3000` 上的单独 API 提供服务。您希望分别在 `app.example.com` 和 `api.example.com` 上公开它们。您还希望使用特定的访问组来保护 API，同时主应用程序保持公开状态。

以下是使用索引标签进行配置的方法：

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: The Web UI ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### 示例分解

* **规则 0 (`app.example.com`)**：
    * 它定义了`dockflare.0.hostname`。
    * 它没有定义 `dockflare.0.service`，因此它回退到基 `dockflare.service` 并使用 `http://my-app:80`。
    * 这是一项公共服务，因为没有为此索引或基础级别定义访问策略。

* **规则 1 (`api.example.com`)**：
    * 它定义了`dockflare.1.hostname`。
    * 它使用 `dockflare.1.service` **覆盖**服务，指向 API 端口 `3000`。
    * 它使用 `dockflare.1.access.group` 应用特定的安全策略。该标签仅影响该规则。

这种方法可以保持标签配置干净并避免重复，使您的 `docker-compose.yml` 文件更易于阅读和维护。