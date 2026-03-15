# 状态持久化

DockFlare 是一个有状态的应用。它需要跟踪自己管理的服务、界面覆盖以及其他配置细节。为了避免在重启或重建 DockFlare 容器时丢失配置，这些状态会持久写入磁盘。

## 状态如何存储

DockFlare 会将状态保存在容器内 `/app/data` 目录下的三个关键文件中：

1. `dockflare_config.dat`：这是最关键的文件。它以**加密**形式保存所有核心设置和敏感信息，包括：
    * 您的 Cloudflare API 令牌和账户 ID
    * DockFlare 管理界面的密码哈希
    * 通过管理界面配置的核心设置，例如隧道名称和区域 ID

2. `agent_keys.dat`：这是一个加密存储，用于保存所有 Agent API 密钥及其元数据（所有者、状态、时间戳）。妥善保护这个文件可以防止旧密钥被重新利用。

3. `state.json`：这个文件以明文 JSON 形式保存托管服务的动态状态，包括：
    * DockFlare 正在管理的所有入口规则，无论它们来自 Docker 标签还是在管理界面中手动创建
    * 应用于 Access Policies 的所有界面覆盖
    * 您创建的全部访问组
    * 已停止但仍处于宽限期内服务的 `pending deletion` 状态

## 持久卷的重要性

由于所有配置都保存在 `/app/data` 目录中，因此将该目录映射到宿主机上的持久卷**非常关键**。

如果不使用持久卷，那么每次删除并重新创建 DockFlare 容器时（例如更新镜像时），**您的所有设置、界面密码和规则配置都会丢失**。

### 推荐的 Docker Compose 配置

推荐的 `docker-compose.yml` 会通过定义命名卷并将其挂载到 `/app/data`，自动解决这个问题：

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

采用这种配置后，`dockflare_config.dat`、`agent_keys.dat` 和 `state.json` 会保存在宿主机上的 `dockflare_data` 目录中，从而在容器更新后仍能安全保留现有设置。

## 备份与恢复

DockFlare 现在会将所有关键数据打包到一个加密备份归档中。Redis 缓存不包含在内，因为它们可以在私有 `dockflare-internal` 网络上安全地重新构建。**设置 → 备份和恢复** 面板可以下载一个 `.zip`，其中包含：

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json`（如果存在）
* 带有用于完整性验证的校验和的清单

恢复归档时，这些文件会被重新创建并重新加载到正在运行的实例中。旧版 `state.json` 上传仍然受支持，但只能恢复规则元数据，之后仍需手动重新输入凭据。
在完成完整归档恢复后，DockFlare 会自动重启容器，以便立即加载加密配置。
