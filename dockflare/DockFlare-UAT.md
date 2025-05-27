DockFlare Testing Script for development only

Pre-requisites:
DockFlare running.
CF_API_TOKEN, CF_ACCOUNT_ID, CF_ZONE_ID correctly configured.
Access to the Cloudflare Dashboard (Tunnel configuration, DNS records for the zone, Access Applications).
A few sample Docker containers with DockFlare labels ready to be started/stopped.
Note down your TUNNEL_NAME or EXTERNAL_TUNNEL_ID.

I. Initial State & Basic UI:
* Test 1.1: Page Load & Initial Display
* Action: Open DockFlare UI in a browser.
* Expected:
* Page loads without console errors.
* Tunnel & Agent status eventually shows correct information (e.g., "Tunnel setup complete", agent "running" or "external").
* "Managed Ingress Rules" table displays existing Docker-managed rules correctly.
* "Add Manual Rule" button is visible.
* Logs stream correctly.
* Test 1.2: Theme Switching
* Action: Use the "Themes" dropdown to select 2-3 different themes.
* Expected: UI theme changes, selection persists on page reload.

II. Docker-Managed Rules (Standard Functionality Check):
* Test 2.1: Start New Labeled Container
* Action: Start a Docker container that has cloudflare.tunnel.enable=true and valid hostname & service labels.
* Expected:
* DockFlare logs show processing for the new container.
* New rule appears in the "Managed Ingress Rules" table with "active" status and correct container ID.
* Cloudflare Dashboard:
* New ingress rule added to the tunnel.
* New CNAME DNS record created.
* Hostname is accessible.
* Test 2.2: Stop Labeled Container
* Action: Stop the container from Test 2.1.
* Expected:
* DockFlare logs show processing for container stop.
* Rule in UI changes to "pending_deletion" with an "Expires At" time.
* Cloudflare: Ingress rule and DNS record still present.
* Test 2.3: Restart Labeled Container (before expiry)
* Action: Before the rule from Test 2.2 expires, restart the same container.
* Expected:
* DockFlare logs show processing for container start.
* Rule in UI changes back to "active", "Expires At" becomes N/A.
* Test 2.4: Rule Expiry and Cleanup (Docker)
* Action: Stop a labeled container (or use one from Test 2.2). Wait for GRACE_PERIOD_SECONDS + CLEANUP_INTERVAL_SECONDS.
* Expected:
* DockFlare logs show cleanup task running and processing the expired rule.
* Rule is removed from the UI.
* Cloudflare Dashboard:
* Ingress rule removed from the tunnel.
* CNAME DNS record removed.
* Associated Access Application (if any was created by labels) is deleted.

III. Manual Rules Management:
* Test 3.1: Add New Manual Rule (HTTP)
* Action: Click "Add Manual Rule". Enter a unique hostname, an HTTP service (e.g., http://192.168.1.100:8080 - use an actual internal IP/port you can test). Select your zone if needed. Submit.
* Expected:
* DockFlare logs show adding the manual rule.
* New rule appears in the "Managed Ingress Rules" table, "Type/Status" shows "Manual", "Identifier" shows "Manual Rule".
* Cloudflare Dashboard:
* New ingress rule added to the tunnel.
* New CNAME DNS record created.
* Hostname is accessible.
* Test 3.2: Add New Manual Rule (HTTPS - No TLS Verify)
* Action: Click "Add Manual Rule". Enter a unique hostname, an HTTPS service using an IP (e.g., https://192.168.1.101:8443 - for a service with a self-signed cert). Check "Disable TLS Verification". Submit.
* Expected:
* Same as 3.1, but the ingress rule in Cloudflare should have noTLSVerify: true.
* Hostname is accessible.
* Test 3.3: Add New Manual Rule (HTTPS - With Path - Test Path Stripping)
### NOT IMPLEMENTED YET
* Action: Click "Add Manual Rule". Enter https://192.168.1.102:8006/some/path (not implemented path stripping yet, will fail as per previous log; not implement it yet). ## !!! ##
* Expected (with path stripping):
* Rule added successfully.
* The service in Cloudflare ingress config should be https://192.168.1.102:8006 (no path).
* Accessing yourhostname.example.com/some/path should work.
* Expected (without path stripping): API error logged by DockFlare, rule not added to CF.
### NOT IMPLEMENTED YET
* Test 3.4: Delete Manual Rule
* Action: For one of the manual rules created, click its "Delete" button. Confirm.
* Expected:
* DockFlare logs show deleting the manual rule.
* Rule is removed from the UI.
* state.json updated.
* Cloudflare Dashboard:
* Ingress rule removed.
* DNS record removed.
* Associated Access Application (if any) removed.
* Test 3.5: Edit Access Policy for Manual Rule
* Action: For an existing manual rule, click "Edit Policy". Change to "Authenticate by Email" and enter your email. Save.
* Expected:
* UI updates policy display. UI Override badge appears.
* Cloudflare Access Application created/updated.
* Hostname now requires authentication.
* Test 3.6: Revert Access Policy for Manual Rule
* Action: For the rule from 3.5, click "Revert". Confirm.
* Expected:
* UI updates policy display (likely to "None (Public)" or reflects TLD policy). UI Override badge removed.
* Cloudflare Access Application deleted.
* Hostname becomes public again (or subject to TLD policy).

IV. Interaction between Docker and Manual Rules:
* Test 4.1: Docker Label for Existing Manual Hostname
* Action: Create a manual rule (e.g., manual-test.example.com). Then, start a Docker container with labels trying to manage the exact same hostname (cloudflare.tunnel.hostname=manual-test.example.com).
* Expected:
* The manual rule for manual-test.example.com should remain in the UI and in Cloudflare, unchanged.
* DockFlare logs should show a warning that the Docker container is attempting to manage an existing manual entry and is skipping it.
* No new ingress/DNS created by the Docker container for this specific hostname.
* Test 4.2: Manual Rule for Existing Docker Hostname (Should be prevented by UI/backend if implemented)
* Action: Have an active Docker-managed rule (e.g., docker-test.example.com). Try to add a manual rule with the same hostname via the UI.
* Expected:
* The ui_add_manual_rule backend should prevent this, returning an error/warning message. "Error: Hostname ... is already managed by Docker labels."
* No changes to the existing Docker-managed rule.

V. Reconciliation and Cleanup Robustness:
* Test 5.1: Reconciliation with Mixed Rules
* Action: Have a mix of active Docker rules, active manual rules, and one Docker rule that is pending_deletion. Trigger reconciliation (or wait).
* Expected:
* Active Docker rules remain active.
* Active manual rules remain active.
* pending_deletion Docker rule remains pending_deletion.
* No unexpected changes. Ingress rules in Cloudflare reflect this state.
* Test 5.2: Stop DockFlare, Manually Delete Ingress from CF, Restart DockFlare
* Action:
1. Have an active DockFlare-managed rule (Docker or manual).
2. Stop DockFlare.
3. Go to Cloudflare Dashboard and manually delete the ingress rule for that hostname (leave DNS if you want, or delete that too).
4. Start DockFlare.
* Expected:
* On startup/reconciliation, DockFlare should detect the discrepancy.
* It should re-add the missing ingress rule to Cloudflare based on its managed_rules state.
* It should re-create/verify the DNS record.
* Test 5.3: Stop DockFlare, Manually Add External Rule to CF, Restart DockFlare
* Action:
1. Stop DockFlare.
2. Go to Cloudflare Dashboard for the DockFlare-managed tunnel. Manually add a new public hostname (e.g., external-cf.example.com pointing to http_status:503).
3. Start DockFlare.
* Expected (with the "Simplified and More Assertive update_cloudflare_config"):
* DockFlare's update_cloudflare_config will see external-cf.example.com.
* Since it's not in managed_rules and not a wildcard/catch-all, DockFlare will remove it from the Cloudflare tunnel configuration. This tests the "DockFlare is master" behavior for its managed tunnel.
* If it was a wildcard (*.external.example.com), it should be preserved.

VI. Edge Cases (Optional but good):
* Test 6.1: Invalid Service URL for Manual Rule
* Action: Try to add a manual rule with an invalid service URL (e.g., justsometext, http://).
* Expected: UI/backend prevents addition, shows an error message.
* Test 6.2: Zone Name Issues for Manual Rule
* Action: If CF_ZONE_ID is not set, try adding a manual rule without specifying a zone.
* Expected: Error, rule not added.
* Action: Specify a non-existent zone name.
* Expected: Error, rule not added.