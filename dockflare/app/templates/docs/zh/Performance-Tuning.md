# 性能调整

对于绝大多数用户来说，DockFlare 的默认设置提供了性能和资源利用率的良好平衡。但是，在非常大或高度动态的环境中，您可能会受益于调整一些与性能相关的高级参数。

这些设置是通过 `docker-compose.yml` 文件中的环境变量进行配置的。

---

## `CLEANUP_INTERVAL_SECONDS`

该变量控制 DockFlare 的后台任务运行以清理过期资源的频率（即，来自宽限期已过的已停止容器的规则）。

* **默认值：** `60` 秒
* **描述：** 较短的间隔意味着可以更快地从您的 Cloudflare 配置中删除过时的资源。较长的间隔会降低后台检查的频率，从而稍微降低资源使用量。
* **何时调整：** 如果您有一个非常动态的环境，其中有许多短期容器，并且希望几乎立即清理它们的资源，您可以降低此值（例如，降低到 `30`）。对于大多数用户来说，默认值就可以了。

**示例：**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

该变量设置 DockFlare 一次执行的并发 DNS 操作（创建、删除）的最大数量。

* **默认值：** `3`
* **描述：** 这是一个针对具有大量服务的环境的直接性能调节旋钮。当 DockFlare 启动或同时启动多个容器时，此设置会限制向 Cloudflare API 发出 DNS 更改的并行请求的数量。
* **何时调整：** 如果您正在管理数百个服务，并注意到初始启动或大规模部署创建所有 DNS 记录的速度很慢，您可以尝试增加此值（例如，增加到 `5` 或 `10`）。请注意，将此值设置得太高可能会导致 Cloudflare API 速率限制。

**示例：**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

这控制各种后台协调任务的批量大小。

* **默认值：** `3`
* **描述：** DockFlare 中的一些后台任务会批量处理项目，以避免系统或 Cloudflare API 不堪重负。此设置控制这些批次的大小。
* **何时调整：** 这是一个非常高级的设置。对于大多数用户来说，不应更改默认值。如果您有大量规则（数百或数千），您可以尝试使用稍大的批量大小，但这通常没有必要。

**示例：**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

此变量更改 DockFlare 发现容器 IP 地址的方式。

* **默认值：** `false`
* **描述：** 默认情况下，DockFlare 期望目标容器与 DockFlare 本身位于同一 Docker 网络上。当 `SCAN_ALL_NETWORKS` 设置为 `true` 时，DockFlare 将检查容器附加的所有网络以查找共享网络。
* **何时调整：** 仅当您有复杂的 Docker 网络设置且您的应用程序容器与 DockFlare 不在同一网络上时才应启用此功能。请注意，启用此功能可能会对具有大量 Docker 网络的环境中的性能产生影响，因为它需要 DockFlare 进行更多检查工作。

**示例：**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```