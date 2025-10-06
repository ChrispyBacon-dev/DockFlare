#!/bin/bash
# Test script for Cloudflare Identity Provider API endpoints
# Replace CF_API_TOKEN and CF_ACCOUNT_ID with your actual credentials

# Set your credentials here
export CF_API_TOKEN="API TOKEN"
export CF_ACCOUNT_ID="CF ACCOUNT ID"

BASE_URL="https://api.cloudflare.com/client/v4"

echo "========================================="
echo "Cloudflare Identity Provider API Tests"
echo "========================================="
echo ""

# Test 1: Verify API Token (Account-scoped endpoint)
echo "1. Verifying API Token..."
echo "---"
curl -s -X GET "${BASE_URL}/accounts/${CF_ACCOUNT_ID}/tokens/verify" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo ""
echo ""

# Test 2: List all Identity Providers
echo "2. Listing all Identity Providers..."
echo "---"
curl -s -X GET "${BASE_URL}/accounts/${CF_ACCOUNT_ID}/access/identity_providers" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo ""
echo ""

# Test 3: Create Google Identity Provider (Example payload - DO NOT RUN without real credentials)
echo "3. Example: Create Google Identity Provider"
echo "---"
echo "POST ${BASE_URL}/accounts/${CF_ACCOUNT_ID}/access/identity_providers"
cat <<'EOF'
{
  "name": "Google Workspace",
  "type": "google-apps",
  "config": {
    "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
    "apps_domain": "yourdomain.com"
  }
}
EOF
echo ""
echo ""

# Test 4: Example - Create Azure AD Identity Provider
echo "4. Example: Create Azure AD Identity Provider"
echo "---"
cat <<'EOF'
{
  "name": "Azure AD",
  "type": "azureAD",
  "config": {
    "client_id": "YOUR_AZURE_CLIENT_ID",
    "client_secret": "YOUR_AZURE_CLIENT_SECRET",
    "directory_id": "YOUR_TENANT_ID"
  }
}
EOF
echo ""
echo ""

# Test 5: Example - Create Generic OIDC Identity Provider
echo "5. Example: Create Generic OIDC Identity Provider"
echo "---"
cat <<'EOF'
{
  "name": "Generic OIDC",
  "type": "oidc",
  "config": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_url": "https://your-provider.com/oauth2/authorize",
    "token_url": "https://your-provider.com/oauth2/token",
    "certs_url": "https://your-provider.com/.well-known/jwks.json"
  }
}
EOF
echo ""
echo ""

# Test 6: Get specific IdP details (Google IdP from list above)
echo "6. Getting specific Identity Provider (Google)..."
echo "---"
GOOGLE_IDP_ID="PUT_GOOGLE_IDP_ID_HERE"  # Replace with actual IdP ID from list
curl -s -X GET "${BASE_URL}/accounts/${CF_ACCOUNT_ID}/access/identity_providers/${GOOGLE_IDP_ID}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo ""
echo ""

# Test 7: Analyze IdP Structure
echo "7. IdP Structure Analysis..."
echo "---"
echo "From the API response, we can see:"
echo "• IdP Types found: 'onetimepin', 'google'"
echo "• Each IdP has: id, type, uid, name, version, config, scim_config"
echo "• Google config includes: client_id, redirect_url"
echo "• Note: client_secret is NOT returned (security)"
echo ""
echo ""

# Test 8: Check supported IdP types from documentation
echo "8. Supported IdP Types (from Cloudflare docs)..."
echo "---"
cat <<'EOF'
Common IdP types:
- onetimepin     : One-time PIN (email-based)
- google         : Google (consumer accounts)
- google-apps    : Google Workspace
- azureAD        : Microsoft Azure AD
- okta           : Okta
- github         : GitHub
- saml           : Generic SAML 2.0
- oidc           : Generic OpenID Connect
- yubico         : Yubico OTP
- linkedin       : LinkedIn
- facebook       : Facebook
EOF
echo ""
echo ""

echo "========================================="
echo "Required API Token Permissions:"
echo "========================================="
echo "✓ Access: Organizations, Identity Providers, and Groups - Edit"
echo "✓ Account: Access - Read"
echo ""
echo "To get a valid API token:"
echo "1. Go to https://dash.cloudflare.com/profile/api-tokens"
echo "2. Create Token > Custom Token"
echo "3. Add permissions listed above"
echo "4. Set Account Resources to your account"
echo ""
