# DockFlare v3.0.3 Security Fix Implementation Plan

**Date:** October 5, 2025
**Issue:** Critical authentication bypass on IdP management endpoints
**Root Cause:** Combination of `DISABLE_PASSWORD_LOGIN` feature + `request_loader` auto-authentication + missing `@login_required` decorators

---

## Root Cause Analysis

### Problem 1: DISABLE_PASSWORD_LOGIN Auto-Login (USER CONFIGURATION)

**Your Instance:** You have `DISABLE_PASSWORD_LOGIN=True` enabled in Settings

**Impact:** When enabled, ANY unauthenticated request is automatically logged in as `User('anonymous')`:

```python
# File: dockflare/app/__init__.py:135-140
if app_instance.config.get('DISABLE_PASSWORD_LOGIN', False):
    from flask_login import login_user
    from app.core.user import User
    user = User('anonymous', auth_method='disabled')
    login_user(user)  # ⚠️ AUTO-LOGIN WITHOUT CREDENTIALS
    return redirect(request.url)
```

**This is INTENDED behavior** for deployments behind a reverse proxy with external authentication (e.g., Cloudflare Access protecting DockFlare itself). However, it completely bypasses authentication when used in normal deployments.

### Problem 2: request_loader Auto-Authentication (CODE ISSUE)

**All Instances:** Even with `DISABLE_PASSWORD_LOGIN=False`, all `api_v2.*` endpoints get auto-authenticated:

```python
# File: dockflare/app/__init__.py:161-163
elif request.endpoint and request.endpoint.startswith('api_v2.'):
    from app.core.user import User
    return User('api_user')  # ⚠️ AUTO-AUTH FOR ALL API ENDPOINTS
```

This was intended to allow MASTER_API_KEY authentication for programmatic API access, but it inadvertently authenticates endpoints in `_UI_ENDPOINT_ALLOWLIST` that should require session-based login.

### Problem 3: Missing @login_required Decorators (CODE ISSUE)

**All Instances:** New IdP endpoints lack `@login_required`:

```python
# File: dockflare/app/web/api_v2_routes.py:2437-2438
@api_v2_bp.route('/idp/sync', methods=['POST'])
def api_sync_idps():  # ⚠️ NO @login_required
```

---

## Is DISABLE_PASSWORD_LOGIN the Root Cause?

**YES and NO:**

### ✅ YES - For Your Instance
- **Your configuration:** You have `DISABLE_PASSWORD_LOGIN=True` enabled
- **Your impact:** This is why you can access everything without login
- **Your fix:** Disable this setting UNLESS you're running DockFlare behind an authentication proxy

### ⚠️ NO - For General Deployments
- **Default configuration:** `DISABLE_PASSWORD_LOGIN=False`
- **Still vulnerable:** The `request_loader` + missing `@login_required` still allows unauthenticated API access
- **Why:** The `request_loader` auto-authenticates all `api_v2.*` endpoints as `'api_user'`, bypassing the need for MASTER_API_KEY on allowlisted endpoints

---

## Two-Part Security Fix

### Part A: Architectural Fix (For All Users)

Fix the `request_loader` to NOT auto-authenticate UI-intended endpoints:

```python
# File: dockflare/app/__init__.py

@login_manager.request_loader
def load_user_from_request(request):
    """Load user from request - bypass session auth for designated API endpoints."""

    if request.path.startswith('/api/v2/auth/'):
        return None

    elif request.endpoint and request.endpoint.startswith('api_v2.'):
        # ✅ FIX: Check if endpoint is UI-only (should use session auth)
        from app.web.api_v2_routes import _UI_ENDPOINT_ALLOWLIST
        if request.endpoint in _UI_ENDPOINT_ALLOWLIST:
            # UI endpoints must use session-based auth via @login_required
            return None

        # API endpoints can use MASTER_API_KEY (handled by before_request)
        from app.core.user import User
        return User('api_user')

    return None
```

### Part B: Defense-in-Depth (Add @login_required)

Add `@login_required` decorators to all UI-intended endpoints:

```python
# File: dockflare/app/web/api_v2_routes.py

from flask_login import login_required

@api_v2_bp.route('/idp/types', methods=['GET'])
@login_required  # ✅ ADD
def api_get_idp_types():
    # ...

@api_v2_bp.route('/idp/list', methods=['GET'])
@login_required  # ✅ ADD
def api_list_idps():
    # ...

@api_v2_bp.route('/idp/sync', methods=['POST'])
@login_required  # ✅ ADD
def api_sync_idps():
    # ...

@api_v2_bp.route('/idp/create', methods=['POST'])
@login_required  # ✅ ADD
def api_create_idp():
    # ...

@api_v2_bp.route('/idp/<friendly_name>', methods=['GET'])
@login_required  # ✅ ADD
def api_get_idp(friendly_name):
    # ...

@api_v2_bp.route('/idp/<friendly_name>', methods=['PUT'])
@login_required  # ✅ ADD
def api_update_idp(friendly_name):
    # ...

@api_v2_bp.route('/idp/<friendly_name>', methods=['DELETE'])
@login_required  # ✅ ADD
def api_delete_idp(friendly_name):
    # ...

@api_v2_bp.route('/zone-policies', methods=['GET'])
@login_required  # ✅ ADD
def get_zone_policies_api():
    # ...

# Also add to auth management endpoints (they're also in allowlist)
@api_v2_bp.route('/auth/settings', methods=['GET', 'PUT'])
@login_required  # Already present - verify
def manage_auth_settings():
    # ...
```

---

## Testing Strategy

### Pre-Fix Testing (Verify Vulnerability)

1. **With DISABLE_PASSWORD_LOGIN=True (Your Current Setup):**
```bash
# Should succeed (vulnerable)
curl -s http://localhost:5001/api/v2/idp/list
```

2. **With DISABLE_PASSWORD_LOGIN=False:**
```bash
# Set in Settings UI, then test
curl -s http://localhost:5001/api/v2/idp/list
# Should still succeed (still vulnerable due to request_loader)
```

### Post-Fix Testing (Verify Fix)

1. **Test unauthenticated access is blocked:**
```bash
# Should return 401 Unauthorized
curl -s -b /dev/null http://localhost:5001/api/v2/idp/list
```

2. **Test authenticated UI access still works:**
```bash
# Login via browser
# Open http://localhost:5001/access-policies
# Should load IdP data via AJAX (uses session cookie)
```

3. **Test MASTER_API_KEY still works for non-UI endpoints:**
```bash
# Should succeed with Bearer token
curl -s -H "Authorization: Bearer YOUR_MASTER_API_KEY" \
  http://localhost:5001/api/v2/services
```

---

## UI Compatibility Verification

### How UI Currently Calls IdP Endpoints

**File:** `dockflare/app/templates/access_policies.html:504`
```javascript
fetch('/api/v2/idp/list')
    .then(response => response.json())
    .then(data => {
        // Render IdP list
    });
```

**Current behavior (VULNERABLE):**
- Browser makes fetch request WITHOUT credentials
- `request_loader` auto-authenticates as `'api_user'`
- Endpoint bypasses MASTER_API_KEY (in allowlist)
- Returns data successfully

**After fix (SECURE):**
- Browser makes fetch request WITH session cookie (automatic in browser)
- `request_loader` returns `None` (endpoint in allowlist)
- `@login_required` checks session cookie
- If valid session: returns data
- If no session: returns 401

### Will UI Break After Fix?

**NO - It will work correctly:**

1. **User logs into DockFlare UI** (via password or OAuth)
2. **Session cookie is set** by Flask-Login
3. **Browser automatically includes cookie** in AJAX requests (same-origin)
4. **`@login_required` validates session** and allows access
5. **UI works as expected**

### Why It Works

- ✅ **Same-Origin:** AJAX calls are from the same domain (cookies sent automatically)
- ✅ **Session-Based:** Browser maintains session cookie after login
- ✅ **No CORS Issues:** Not cross-origin, so credentials are included by default
- ✅ **CSRF Token:** Already handled by Flask-WTF for POST/PUT/DELETE (if needed)

---

## Implementation Steps

### Step 1: Fix request_loader (Immediate)

```bash
# Edit: dockflare/app/__init__.py
# Modify load_user_from_request() function (lines 154-165)
```

### Step 2: Add @login_required Decorators (Immediate)

```bash
# Edit: dockflare/app/web/api_v2_routes.py
# Add decorator to 8 endpoints (IdP + zone-policies)
```

### Step 3: Test with DISABLE_PASSWORD_LOGIN=True (Verify Fix for Your Config)

```bash
# Keep setting enabled
# Restart DockFlare
# Test unauthenticated curl (should fail)
# Test UI access (should work via auto-login)
```

### Step 4: Test with DISABLE_PASSWORD_LOGIN=False (Verify General Security)

```bash
# Disable setting in UI
# Restart DockFlare
# Test unauthenticated curl (should fail)
# Test UI after login (should work)
```

---

## DISABLE_PASSWORD_LOGIN Use Cases

### ✅ SAFE Use Case - Behind External Auth Proxy

**Scenario:** DockFlare is protected by Cloudflare Access or another authentication proxy

**Setup:**
1. Cloudflare Access policy requires SSO login to reach DockFlare
2. Only authenticated users can reach `http://localhost:5001`
3. DockFlare sets `DISABLE_PASSWORD_LOGIN=True`
4. Users are auto-logged in as 'anonymous' (external auth already verified)

**Security:** ✅ SAFE - External layer provides authentication

### ❌ UNSAFE Use Case - Direct Internet Exposure

**Scenario:** DockFlare exposed directly without external authentication

**Setup:**
1. DockFlare accessible at `https://dockflare.example.com` directly
2. `DISABLE_PASSWORD_LOGIN=True` enabled
3. No external authentication layer

**Security:** 🔴 CRITICAL - Anyone can access without credentials

---

## Your Specific Situation

**Your Config:** `DISABLE_PASSWORD_LOGIN=True` on `localhost:5001`

**Question:** Is DockFlare behind an external authentication proxy?

### If NO (Direct Access):
**Recommendation:**
1. **Disable this setting immediately** via Settings UI
2. Use password or OAuth login
3. Apply the code fixes above
4. Re-test security

### If YES (Behind Cloudflare Access or similar):
**Recommendation:**
1. Apply the code fixes above
2. **Keep setting enabled** (intended behavior)
3. Ensure external auth layer is properly configured
4. Test that unauthenticated requests to external proxy are blocked

---

## Migration Plan for Existing Users

### Release Notes Warning

```markdown
## Security Fix - Authentication on IdP Endpoints

v3.0.3 had a critical authentication bypass vulnerability. v3.0.4 fixes this issue.

### Breaking Change for DISABLE_PASSWORD_LOGIN Users

If you have "Disable Password Login" enabled:
- ✅ If DockFlare is behind an auth proxy (Cloudflare Access, etc.): No action needed
- ⚠️ If DockFlare is directly accessible: Disable this setting immediately

After upgrading to v3.0.4:
1. Verify you can still log into DockFlare UI
2. Test Access Policies page loads IdP data
3. Check browser console for 401 errors (indicates session issue)
```

---

## Alternative: Remove Endpoints from Allowlist

**Instead of adding `@login_required`, require MASTER_API_KEY:**

### Pros:
- More secure (API key vs session cookie)
- Better separation of UI and API concerns

### Cons:
- **Breaks existing UI implementation**
- Requires JavaScript changes to pass MASTER_API_KEY in AJAX headers
- Exposes MASTER_API_KEY to browser (localStorage or hardcoded in JS)
- Not recommended for UI-initiated calls

### Why We DON'T Recommend This:

1. **MASTER_API_KEY in Browser = Security Risk**
   - If stored in localStorage/sessionStorage, vulnerable to XSS
   - If embedded in HTML/JS, visible to all users
   - MASTER_API_KEY is meant for server-to-server API calls, not browser calls

2. **Session Cookies = Designed for Browser Auth**
   - HttpOnly flag prevents XSS access
   - SameSite prevents CSRF
   - Automatic expiration and renewal
   - Industry standard for browser-based authentication

**Conclusion:** Use `@login_required` (session-based) for UI-initiated API calls.

---

## Recommended Fix (Final)

### Minimal Changes, Maximum Security:

1. **Fix `request_loader` in `__init__.py`** (10 lines changed)
2. **Add `@login_required` to 8 endpoints in `api_v2_routes.py`** (8 lines added)
3. **No JavaScript changes required**
4. **No database migrations required**
5. **Backwards compatible with existing UI**

### Total Code Changes: ~18 lines

---

## Next Steps

1. **Confirm:** Is your DockFlare instance behind an external auth proxy?
2. **Decision:** Should we proceed with the fix implementation?
3. **Testing:** Can you test on localhost:5001 before deploying?

Let me know your answers and I'll implement the fixes.
