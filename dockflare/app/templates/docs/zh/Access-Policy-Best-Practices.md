# 访问策略最佳实践与示例

DockFlare 最强大的安全能力之一是**访问组**。它们提供了一种集中、可复用且易维护的方式，通过 Cloudflare Zero Trust 保护您的服务。

## “黄金法则”：使用访问组

最重要的最佳实践是**将访问组用于所有常见访问策略**。

访问组是您在 DockFlare Web UI 中创建的策略模板。您无需在每个容器上用多个标签定义复杂规则，只需创建一次策略并用一个标签应用即可。DockFlare v3.0.3 会将每个访问组同步为 Cloudflare 可复用策略，因此同一组决策规则可以被多个应用共用。

---

## 如何创建和使用访问组

创建访问组是一个完全在 DockFlare UI 内完成的简单过程。

### 第 1 步：创建访问组

1. 从 DockFlare UI 的主导航栏导航至 **访问策略** 页面。
2. 单击**“添加访问组”**按钮。
3. 为该访问组设置一个**唯一且具有描述性的 ID**。您将在 Docker 标签中使用此 ID。例如：`admin-users`、`home-network`、`geo-block`。
4. 从模式顶部的选项卡中选择 **访问模式**：
    * **经过身份验证** 要求用户登录并发出 `allow` 决策。
    * **Public** 使用 `bypass` 决策，使应用保持公开，同时仍可应用地理过滤等限制。
5. 填写针对所选模式显示的输入内容（经过身份验证的电子邮件，以及两者的可选国家/地区列表）。
6. 调整可选设置，例如会话持续时间、应用程序启动器可见性和自动 IdP 重定向（如果您处于身份验证模式）。
7. 保存访问组。DockFlare 会在本地写入定义，并将其作为 `DockFlare-AccessGroup-<id>` 同步到 Cloudflare。

### 步骤 2：应用访问组

创建后，您可以通过两种方式将访问组应用到服务：

#### A) 使用 Docker 标签（推荐方式）

对于任何新的或现有的容器，只需添加 `dockflare.access.group` 标签以及您创建的组的 ID。

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
您还可以通过使用 `dockflare.access.groups` 和以逗号分隔的 ID 列表来应用多个组：
`dockflare.access.groups=admin-users,home-network`

#### 系统管理策略

DockFlare 提供了两个自动可用的内置系统策略：

- **`public-default-bypass`** - 具有旁路决策的公共访问（用于真正的公共服务）
- **`authenticated-default`** - 使用一次性 PIN + 电子邮件限制的默认身份验证

这些系统策略是不可删除的，并作为区域保护和旧标签迁移的基础。

#### B) 通过 Web UI（用于手动规则或覆盖）

您还可以直接从仪表板将访问组应用于任何规则：
1. 在主仪表板上找到您要修改的入口规则。
2. 单击**“管理规则”**按钮。
3. 在编辑模式中，从“访问组”下拉菜单中选择所需的访问组。
4. 保存更改。

这非常适合将策略应用于手动创建的规则（对于非 Docker 服务）或临时覆盖由 Docker 标签定义的策略。

---

## 策略示例

以下是您可以在访问组中创建的一些常见策略配置。

### 示例 1：通过电子邮件进行身份验证

这是最常见的用例：仅允许可以通过您配置的身份提供商（例如 Google、GitHub 或发送到其电子邮件的一次性 PIN）进行身份验证的特定用户。

* **组ID：** `admin-users`
* **模式：** *已验证*
* **允许的电子邮件：** `user1@example.com`、`user2@example.com`
* **会话持续时间：** `24h`

DockFlare 会创建一个可复用策略：对列出的邮箱返回 `allow` 决策，并对其余用户应用默认 `deny`。使用 `dockflare.access.group=admin-users` 应用该访问组。

### 示例 2：允许您的家庭 IP 地址

此策略限制对家庭网络的访问，允许您在使用受信任的 IP 时跳过登录提示，同时在其他地方强制执行身份验证。

1. **查找您的公共 IP：** 在浏览器中，搜索“what is my ip”。将显示您的公共 IP 地址（例如 `203.0.113.55`）。
2. **创建访问组：**
    * **组ID：** `home-network`
    * **模式：** *已验证*
    * **允许的电子邮件：** `you@example.com`
    * **绕过 IP：** 将 `203.0.113.55/32` 添加到 IP 白名单字段

DockFlare 生成一个策略，首先绕过您的 IP 范围，然后要求列出的电子邮件进行身份验证。其他人都会收到拒绝决定。

### 示例 3：地理围栏（阻止多个国家/地区）

此政策使您的营销网站保持公开状态，同时限制来自特定区域的流量。

* **组ID：** `public-eu`
* **模式：** *公共*
* **被阻止的国家/地区：** `RU`、`CN`、`KP`

由此产生的可重用政策向所有人发出 Cloudflare `bypass` 决定，所列国家/地区除外。如果您需要分层附加控件 (`dockflare.access.groups=public-eu,admin-users`)，请将其与其他组结合起来。

---

## 区域默认策略 - 安全最佳实践

### 什么是区域默认策略？

区域默认策略是通配符 `*.domain.com` 访问应用程序，用于保护 DNS 区域的所有子域，包括您尚未明确配置的子域。

### 为什么你需要它们

**问题：** 如果您忘记向服务添加访问策略，则默认情况下它会公开。

**解决方案：** 区域级通配符策略充当安全网。即使您忘记配置 `forgotten-service.yourdomain.com`，`*.yourdomain.com` 策略也会捕获它。

### 如何设置它们

1. 导航至 **访问策略** 页面
2. 滚动到 **区域默认策略（*.tld 通配符）** 部分
3. 寻找带有“不受保护”⚠️ 徽章的区域
4. 单击“**创建策略**”
5. 选择适当的访问组：
   - **对于公共领域：** 使用 `public-default-bypass`
   - **对于内部域：** 使用身份验证策略
   - **对于混合用途：** 使用最严格的政策

### 最佳实践

- ✅ **始终为生产域创建区域策略**
- ✅ **对内部/私有区域使用身份验证策略**
- ✅ **仅对真正的公共区域使用公共旁路**
- ✅ **定期审查** - 每月检查区域保护状态
- ⚠️ **记住优先级** - 特定主机名策略覆盖通配符策略

### 策略优先顺序

Cloudflare 按以下顺序评估访问策略：

1. **精确主机名匹配**（例如，`app.example.com`）- 最高优先级
2. **通配符匹配**（例如，`*.example.com`）- 后备
3. **不匹配** = 公共访问（无访问应用程序）- 默认

这意味着您可以拥有限制性区域默认策略，并且仍然为各个服务创建特定的例外。

---

## 管理外部 Cloudflare 策略

### 了解策略类型

DockFlare 在“访问策略”页面中显示三种类型的策略，每种策略都有一个可视徽章：

- **🟦 DockFlare** - 由 DockFlare 创建和管理的策略（前缀：`DockFlare-`）
- **🟪 外部** - 在 DockFlare 外部创建的策略（手动或其他工具）
- **🟧 系统** - 不可删除的系统策略（`public-default-bypass`、`authenticated-default`）

### 同步外部策略

默认情况下，DockFlare 仅导入带有 `DockFlare-` 前缀的策略。这使您的策略列表保持干净并专注于容器基础设施。

**要同步所有 Cloudflare 策略**（包括手动创建的策略）：

1.设置环境变量：`SYNC_ALL_CLOUDFLARE_POLICIES=true`
2.重启DockFlare
3. 在访问策略页面上单击 **“从 Cloudflare 同步”**

外部策略将显示带有紫色 **“外部”** 徽章。

### 为什么要导入外部策略？

**优点：**
- 完整了解整个 Cloudflare Access 设置
- 重用现有策略而不重新创建它们
- 在一个界面中集中管理
- 将任何策略应用于任何服务（是否由 DockFlare 管理）

**缺点：**
- 如果您有许多外部政策，则政策列表更长
- 意外修改非 DockFlare 服务使用的策略的风险

### 组织您的政策

**专业提示：** 在 Cloudflare 中重命名外部策略以使用 `DockFlare-` 前缀

您可以通过在 Cloudflare 仪表板中重命名外部策略来组织外部策略：

1. 在 **Cloudflare 零信任** 中打开策略
2. 将其重命名为使用 `DockFlare-` 前缀（例如 `DockFlare-LegacyVPN` 或 `DockFlare-ThirdPartyApp`）
3. 在 DockFlare 中点击 **“从 Cloudflare 同步”**
4. 该策略现在显示为 **DockFlare 管理** 策略（蓝色徽章）

这使您能够：
- ✅ 使用一致的命名对所有 DockFlare 可见的策略进行分组
- ✅ 按类型过滤和排序政策
- ✅ 区分“由 DockFlare 管理”和“仅在 DockFlare 中可见”

### 过滤策略

使用 **Filter** 下拉列表查看特定策略类型：

- **所有策略** - 显示所有内容（DockFlare、外部、系统）
- **DockFlare-Managed** - 仅显示蓝色标记的策略
- **外部** - 仅显示紫色徽章的政策
- **系统** - 仅显示系统策略

### 安全特性

**外部政策保护：**

删除或编辑外部策略时，DockFlare 会显示警告：

> ⚠️ 警告：这是一个外部策略，不是由 DockFlare 创建的。
>
> 修改此策略可能会影响 DockFlare 之外的服务。
>
> 你绝对确定吗？

这可以防止意外更改其他工具或手动配置管理的策略。

### 最佳实践

1. **默认设置（推荐）：**
   - 保留 `SYNC_ALL_CLOUDFLARE_POLICIES=false` （默认）
   - 仅显示 DockFlare 管理的策略
   - 清晰、重点突出的政策清单

2. **高级设置（高级用户）：**
   - 启用 `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - 在一个地方查看和管理所有政策
   - 将组织的外部策略重命名为 `DockFlare-` 前缀

3. **混合方法：**
   - 默认情况下保持同步禁用
   - 在 Cloudflare 中手动将重要的外部策略重命名为 `DockFlare-*`
   - 它们会在下次同步后自动出现

4. **策略命名约定：**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
