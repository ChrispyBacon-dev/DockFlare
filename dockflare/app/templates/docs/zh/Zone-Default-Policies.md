# 区域默认策略 - 通配符保护

## 概述

区域默认策略是一项安全最佳实践功能，它使用 Cloudflare Access 通配符应用程序 (`*.domain.com`) 自动保护 DNS 区域的所有子域。

## 这解决的问题

没有区域默认策略：
- 被遗忘的服务被公开暴露
- 新的子域在手动配置之前没有保护
- 主机名配置中的拼写错误绕过访问控制
- 文档漂移导致安全漏洞

## 它是如何工作的

### 政策优先级

Cloudflare 按以下顺序评估访问策略：

1. **主机名精确匹配**（例如，`app.example.com`）
2. **通配符匹配**（例如，`*.example.com`）
3. **不匹配** = 公共访问（无访问应用程序）

### DockFlare 实施

DockFlare 的 **区域默认策略** 部分：
- 列出您的所有 Cloudflare DNS 区域
- 通过视觉徽章显示保护状态
- 允许一键创建 `*.zone.com` 策略
- 让您选择哪个访问组保护该区域

## 设置指南

### 第 1 步：检查您的区域

1. 导航至 **访问策略** 页面
2. 滚动到**区域默认策略（*.tld 通配符）**
3. 查看保护状态：
   - 🛡️ **绿色“受保护”** - 区域有通配符政策
   - ⚠️ **黄色“未受保护”** - 区域易受攻击

### 第 2 步：创建区域策略

对于每个未受保护的区域：

1. 单击**创建策略**按钮
2. 模态窗口会显示 `*.zone-name.com` 主机名
3. 选择适当的访问策略：
   - **公共区域** → `public-default-bypass`
   - **内部区域** → 身份验证策略
   - **混合区** → 最严格的政策
4. 单击“**创建区域策略**”

### 第 3 步：在 Cloudflare 中验证

1. 打开 Cloudflare 零信任仪表板
2. 导航至访问 → 应用程序
3. 查找名为 `Zone Default: *.domain.com` 的应用程序
4. 验证策略是否正确

## 安全建议

### 生产环境

✅ **始终启用区域默认策略**
- 防止意外暴露
- 捕获配置错误
- 防止子域发现攻击

### 政策选择策略

- **公共内容域**（博客、营销）：`public-default-bypass`
- **内部工具域**：电子邮件/域身份验证
- **敏感数据域**：启用 MFA 的身份验证
- **开发领域**：以最严格的政策锁定

### 监控

定期回顾：
- 哪些区域受到保护（**访问策略**页面）
- 在 Cloudflare 中访问应用程序日志
- 活动子域列表与配置的策略

## 故障排除

### “策略已存在”错误

`*.domain.com` Access 应用程序已存在。这可能是：
- 在 Cloudflare 中手动创建
- 由 DockFlare 先前创建
- 由另一个工具创建

**解决方案：** 直接在 Cloudflare 中管理，或通过 DockFlare 删除并重新创建。

### 服务无需身份验证仍可访问

检查策略优先级：
1. 验证服务是否具有特定的主机名策略
2. 确认区域通配符存在且配置正确
3. 如果尽管有区域保护，服务仍应公开，请添加 `dockflare.access.group=public-default-bypass` 标签

### 为公共服务绕过区域保护

如果您有区域级身份验证策略但需要特定服务保持公开：

1. 给容器添加绕过标签：
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. 这将创建一个具有旁路决策的精确主机名访问应用程序
3. 精确主机名策略覆盖通配符策略
4. 服务可公开访问，同时区域仍受保护

### 区域未显示在列表中

可能的原因：
- DNS 区域不在您的 Cloudflare 帐户中
- API 令牌缺少 `Zone:Zone:Read` 权限
- 区域已暂停或删除

**解决方案：** 验证 Cloudflare 仪表板中存在区域并且 API 令牌具有正确的权限。

## 最佳实践

1. **首先创建区域策略** - 添加服务之前
2. **对内部区域使用身份验证** - 切勿使用旁路
3. **记录例外情况** - 如果某个区域不需要保护，请记录原因
4. **定期审核** - 每月审查区域保护状态
5. **生产前测试** - 验证通配符策略不会破坏现有服务
6. **最小权限原则** - 使用仍允许合法访问的最严格的策略

## 配置示例

### 公共博客区
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### 内部工具区
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### 混合开发区
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## 了解策略优先级

### 场景 1：特定策略覆盖通配符

**设置：**
- 区域策略：`*.example.com` → 需要身份验证
- 具体策略：`blog.example.com` → `public-default-bypass`

**结果：**
- `blog.example.com` → 公共（特定策略获胜）
- `api.example.com` → 需要身份验证（通配符捕获它）
- `forgotten.example.com` → 需要身份验证（通配符捕获它）

### 场景 2：通配符作为安全网

**设置：**
- 区域政策：`*.internal.company.com` → 需要 @company.com 电子邮件
- 具体政策：`test-server.internal.company.com` 无

**结果：**
- `test-server.internal.company.com` → 需要身份验证（通配符保护它）
- 即使您忘记配置它，区域策略也会保护它

### 场景 3：无保护

**设置：**
- 区域策略：`*.risky-domain.com` 无
- 具体策略：`app.risky-domain.com` → 身份验证

**结果：**
- `app.risky-domain.com` → 需要身份验证（特定策略）
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** （没有通配符来捕获它）

## 与 DockFlare 标签集成

### 使用 `default_tld` 标签

`dockflare.access.policy=default_tld` 标签告诉 DockFlare 使用区域的通配符策略：

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**行为：**
- 如果 `*.internal.company.com` 存在 → 继承该策略
- 如果不存在区域策略 → 服务是公共的（未创建 Access 应用程序）

### 推荐

而不是依赖 `default_tld` 标签：
1. 在管理界面中创建区域默认策略
2. 让通配符策略自动保护所有服务
3. 只针对例外情况创建特定策略

默认情况下这可以确保更好的安全性。

## 相关文档

- [访问策略最佳实践](Access-Policy-Best-Practices.md)
- [使用网页管理界面](Using-the-Web-UI.md)
- [容器标签](Container-Labels.md)
- [DockFlare 的工作原理](How-DockFlare-Works.md)
- [安全架构](Security-Architecture.md)
