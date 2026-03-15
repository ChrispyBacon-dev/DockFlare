# Zone Default Policies - Wildcard Protection

## Overview

Zone Default Policies are a security best-practice feature that uses Cloudflare Access wildcard applications (`*.domain.com`) to protect all subdomains of a DNS zone automatically.

## The Problem This Solves

Without zone default policies:
- Forgotten services are publicly exposed
- New subdomains have no protection until manually configured
- Typos in hostname configurations bypass access controls
- Documentation drift leads to security gaps

## How It Works

### Policy Priority

Cloudflare evaluates Access policies in this order:

1. **Exact hostname match** (e.g., `app.example.com`)
2. **Wildcard match** (e.g., `*.example.com`)
3. **No match** = Public access (no Access App)

### DockFlare Implementation

DockFlare's **Zone Default Policies** section:
- Lists all your Cloudflare DNS zones
- Shows protection status with visual badges
- Allows one-click creation of `*.zone.com` policies
- Lets you choose which Access Group protects the zone

## Setup Guide

### Step 1: Review Your Zones

1. Navigate to **Access Policies** page
2. Scroll to **Zone Default Policies (*.tld Wildcards)**
3. Review protection status:
   - 🛡️ **Green "Protected"** - Zone has wildcard policy
   - ⚠️ **Yellow "Not Protected"** - Zone is vulnerable

### Step 2: Create Zone Policies

For each unprotected zone:

1. Click **Create Policy** button
2. Modal shows `*.zone-name.com` hostname
3. Select appropriate Access Policy:
   - **Public zones** → `public-default-bypass`
   - **Internal zones** → Authentication policy
   - **Mixed zones** → Most restrictive policy
4. Click **Create Zone Policy**

### Step 3: Verify in Cloudflare

1. Open Cloudflare Zero Trust dashboard
2. Navigate to Access → Applications
3. Look for applications named `Zone Default: *.domain.com`
4. Verify policy is correct

## Security Recommendations

### Production Environments

✅ **Always enable zone default policies**
- Prevents accidental exposure
- Catches configuration mistakes
- Protects against subdomain discovery attacks

### Policy Selection Strategy

- **Public content domains** (blogs, marketing): `public-default-bypass`
- **Internal tools domains**: Email/domain authentication
- **Sensitive data domains**: MFA-enabled authentication
- **Development domains**: Lock down with strictest policy

### Monitoring

Regularly review:
- Which zones have protection (**Access Policies** page)
- Access Application logs in Cloudflare
- List of active subdomains vs configured policies

## Troubleshooting

### "Policy already exists" error

A `*.domain.com` Access Application already exists. This could be:
- Created manually in Cloudflare
- Created by DockFlare previously
- Created by another tool

**Solution:** Manage it directly in Cloudflare, or delete and recreate via DockFlare.

### Service still accessible without authentication

Check policy priority:
1. Verify service has specific hostname policy
2. Confirm zone wildcard exists and is configured correctly
3. If service should be public despite zone protection, add `dockflare.access.group=public-default-bypass` label

### Bypassing Zone Protection for Public Services

If you have a zone-level authentication policy but need specific services to remain public:

1. Add the bypass label to the container:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. This creates an exact hostname Access Application with bypass decision
3. Exact hostname policies override wildcard policies
4. Service becomes publicly accessible while zone stays protected
3. Check Cloudflare Access logs for policy evaluation order
4. Ensure DNS record points to correct tunnel

### Zone not showing in list

Possible causes:
- DNS zone not in your Cloudflare account
- API token lacks `Zone:Zone:Read` permission
- Zone is paused or deleted

**Solution:** Verify zone exists in Cloudflare dashboard and API token has correct permissions.

## Best Practices

1. **Create zone policies first** - Before adding services
2. **Use authentication for internal zones** - Never use bypass
3. **Document exceptions** - If a zone doesn't need protection, document why
4. **Regular audits** - Monthly review of zone protection status
5. **Test before production** - Verify wildcard policy doesn't break existing services
6. **Principle of least privilege** - Use most restrictive policy that still allows legitimate access

## Example Configurations

### Public Blog Zone
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Internal Tools Zone
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Mixed Development Zone
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Understanding Policy Priority

### Scenario 1: Specific Policy Overrides Wildcard

**Setup:**
- Zone policy: `*.example.com` → Requires authentication
- Specific policy: `blog.example.com` → `public-default-bypass`

**Result:**
- `blog.example.com` → Public (specific policy wins)
- `api.example.com` → Requires auth (wildcard catches it)
- `forgotten.example.com` → Requires auth (wildcard catches it)

### Scenario 2: Wildcard as Safety Net

**Setup:**
- Zone policy: `*.internal.company.com` → Requires @company.com email
- Specific policy: None for `test-server.internal.company.com`

**Result:**
- `test-server.internal.company.com` → Requires auth (wildcard protects it)
- Even if you forgot to configure it, the zone policy protects it

### Scenario 3: No Protection

**Setup:**
- Zone policy: None for `*.risky-domain.com`
- Specific policy: `app.risky-domain.com` → Authentication

**Result:**
- `app.risky-domain.com` → Requires auth (specific policy)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (no wildcard to catch it)

## Integration with DockFlare Labels

### Using `default_tld` Label

The `dockflare.access.policy=default_tld` label tells DockFlare to use the zone's wildcard policy:

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

**Behavior:**
- If `*.internal.company.com` exists → Inherits that policy
- If no zone policy exists → Service is public (no Access App created)

### Recommendation

Instead of relying on `default_tld` label:
1. Create zone default policies in the UI
2. Let the wildcard policy automatically protect all services
3. Only create specific policies for exceptions

This ensures better security by default.

## Related Documentation

- [Access Policy Best Practices](Access-Policy-Best-Practices.md)
- [Using the Web UI](Using-the-Web-UI.md)
- [Container Labels](Container-Labels.md)
- [How DockFlare Works](How-DockFlare-Works.md)
- [Security Architecture](Security-Architecture.md)
