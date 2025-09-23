# Common Issues

This page lists some of the common issues that users may encounter and how to resolve them.

---

### Issue: The DockFlare container fails to start or is in a restart loop.

**Solution:**
1.  **Check the Docker logs:** The first step is always to check the logs of the DockFlare container. Run the following command:
    ```bash
    docker logs dockflare
    ```
2.  **Look for Errors:** Look for any error messages. Common causes include:
    *   An invalid `docker-compose.yml` file (e.g., incorrect syntax, volume mounting issues).
    *   Problems with the Docker daemon itself.
    *   Connectivity or permission issues with the docker-socket-proxy service or the `DOCKER_HOST` setting.

---

### Issue: DNS records are not being created in Cloudflare.

**Solution:**
1.  **Check the DockFlare Logs:** Look for any error messages related to the Cloudflare API. The logs will often tell you exactly why the API call failed.
2.  **Verify API Token Permissions:** This is the most common cause. Ensure that your Cloudflare API Token has the required permissions. At a minimum, you need:
    *   `Zone:DNS:Edit` for every zone you want DockFlare to manage.
    *   `Zone:Zone:Read`
3.  **Verify Zone Configuration:**
    *   Ensure that the **Zone ID** you provided during setup is correct.
    *   If you are using the `dockflare.zonename` label, double-check that the zone name is spelled correctly.

---

### Issue: An Access Policy (Zero Trust) is not being applied to a service.

**Solution:**
1.  **Check API Token Permissions:** Ensure your API token has the `Account:Access: Apps and Policies:Edit` permission.
2.  **Check for UI Overrides:** In the DockFlare dashboard, check if the rule has a "UI Override" status. UI overrides take precedence over labels.
3.  **Check Access Group ID:** If you are using `dockflare.access.group`, make sure the ID you specified in the label **exactly** matches the ID you created for the Access Group on the "Access Policies" page.
4.  **Check the Cloudflare Dashboard:** Log in to your Cloudflare Zero Trust dashboard. Navigate to **Access -> Applications** to see if the Access Application was created. Sometimes, Cloudflare will show an error there that is not visible in the API response.

---

### Issue: I get an `ERR_TOO_MANY_REDIRECTS` error when trying to access my service.

**Solution:**
This error almost always happens due to a misconfiguration of SSL/TLS settings between your origin service and Cloudflare.

1.  **Check Cloudflare SSL/TLS Mode:** In your Cloudflare dashboard, go to the SSL/TLS settings for your domain. Ensure your encryption mode is set to **Full (Strict)**.
2.  **Avoid Double Redirects:** The "Flexible" SSL mode in Cloudflare can cause this issue if your backend application is also trying to redirect from HTTP to HTTPS. The browser gets stuck in a loop.
3.  **Use `https` in your service URL:** If your backend service supports HTTPS, use `https://` in your `dockflare.service` label (e.g., `dockflare.service=https://my-app:443`). This ensures the connection from `cloudflared` to your service is also encrypted.

---

### Issue: The managed `cloudflared-agent` container fails to start with a "stale network" error.

**Solution:**
This can happen if the Docker network the agent was using was removed and recreated. DockFlare is designed to handle this automatically.

1.  **Restart DockFlare:** A simple restart of the DockFlare container (`docker compose restart dockflare`) should resolve this.
2.  **How it Works:** On startup, DockFlare checks the health of its managed agent. If it detects this specific issue, it will automatically remove the broken agent container and create a new one with the correct configuration. This was a specific bug fixed in version `v1.9.5`. Ensure you are on a recent version of DockFlare.
