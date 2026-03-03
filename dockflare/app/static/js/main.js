// app/static/js/main.js - painful .. javascript
const maxLogLines = 250;
let initialConnectMessageCleared = false;
let activeLogSource = null;
let eventSourceHealthCheck = null;
let logsEnabled = false;
let pingInterval = null;
let manualTunnelTomSelect = null;
let cachedTunnels = null;
let cachedZones = null;
let manualZoneDetectionTimeout = null;
let servicesSnapshotPromise = null;
let servicesSnapshotQueued = false;

function getMasterApiKey() {
    const meta = document.querySelector('meta[name="dockflare-api-key"]');
    return meta && meta.content ? meta.content : null;
}

function buildApiHeaders(initial = {}) {
    const headers = { ...initial };
    const key = getMasterApiKey();
    if (key) {
        headers['Authorization'] = `Bearer ${key}`;
    }
    return headers;
}

function initializeAllTomSelects() {
    const multiCheckboxOptions = {
        plugins: {
            'checkbox_options': {},
            'remove_button': {
                title: 'Remove this item',
            }
        },
        create: false,
        sortField: {
            field: "text",
            direction: "asc"
        }
    };
    
    const countrySelectOptions = {
        ...multiCheckboxOptions,
        maxOptions: null, 
    };

    const singleSelectOptions = {
        create: false,
        sortField: {
            field: 'text',
            direction: 'asc'
        }
    };
    
    const addGroupSelect = document.getElementById('manual_access_group');
    if (addGroupSelect) {
        new TomSelect(addGroupSelect, multiCheckboxOptions);
    }
    const editGroupSelect = document.getElementById('edit_manual_access_group');
    if (editGroupSelect) {
        new TomSelect(editGroupSelect, multiCheckboxOptions);
    }

    const manualTunnelSelect = document.getElementById('manual_tunnel_id');
    if (manualTunnelSelect) {
        manualTunnelTomSelect = new TomSelect(manualTunnelSelect, singleSelectOptions);
    }

}

const themeManager = (function() {
    let themeMenuScoped;
    const htmlElementScoped = document.documentElement;
    const availableThemes = [
        "light", "dark", "cupcake", "bumblebee", "emerald", "corporate",
        "synthwave", "retro", "cyberpunk", "valentine", "halloween", "garden",
        "forest", "aqua", "lofi", "pastel", "fantasy", "wireframe", "black",
        "luxury", "dracula", "cmyk", "autumn", "business", "acid",
        "lemonade", "night", "coffee", "winter"
    ];

    function setTheme(theme) {
        if (!availableThemes.includes(theme)) {
            console.warn(`Theme "${theme}" not available, defaulting to light.`);
            theme = 'light';
        }
        localStorage.setItem('theme', theme);
        htmlElementScoped.setAttribute('data-theme', theme);

        if (themeMenuScoped) updateSelectedThemeInMenu(theme);
    }

    function populateThemeMenu() {
        if (!themeMenuScoped) return;
        themeMenuScoped.innerHTML = '';
        availableThemes.forEach(themeName => {
            const listItem = document.createElement('li');
            listItem.classList.add('w-full');
            const link = document.createElement('a');
            link.textContent = themeName.charAt(0).toUpperCase() + themeName.slice(1);
            link.setAttribute('data-theme-value', themeName);
            link.href = "#";
            link.classList.add('flex', 'items-center', 'flex-grow', 'w-full', 'px-4', 'py-2');
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const selectedTheme = e.target.getAttribute('data-theme-value');
                setTheme(selectedTheme);
                if (document.activeElement && typeof document.activeElement.blur === 'function') {
                    document.activeElement.blur();
                }
            });
            listItem.appendChild(link);
            themeMenuScoped.appendChild(listItem);
        });
    }

    function updateSelectedThemeInMenu(currentTheme) {
        if (!themeMenuScoped) return;
        themeMenuScoped.querySelectorAll('li a').forEach(a => {
            if (a.getAttribute('data-theme-value') === currentTheme) {
                a.parentElement.classList.add('font-bold', 'text-primary');
                a.classList.add('active');
            } else {
                a.parentElement.classList.remove('font-bold', 'text-primary');
                a.classList.remove('active');
            }
        });
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('theme');
        const defaultTheme = 'light';
        setTheme(savedTheme || defaultTheme);
    }

    return {
        initialize: function() {
            themeMenuScoped = document.getElementById('theme-menu');
            const themeSelectorBtn = document.getElementById('theme-selector-btn');

            if (themeMenuScoped && themeSelectorBtn) {
                populateThemeMenu();
                initTheme();
            } else {
                console.error("DockFlare Theme Error: UI elements for theme selector not found.");
            }
        }
    };
})();

function initializeEditRuleModal() {
    const editButtons = document.querySelectorAll('.edit-rule-btn');
    const modal = document.getElementById('edit_manual_rule_modal');

    if (!editButtons.length || !modal) {
        return;
    }

    editButtons.forEach(button => {
        button.addEventListener('click', async function() {
            try {
                const ruleKey = this.dataset.ruleKey;
                const details = JSON.parse(this.dataset.ruleDetails);

                modal.querySelector('#edit_original_rule_key').value = ruleKey;

                const hostname = details.hostname || '';
                const parts = hostname.split('.');
                if (parts.length > 2 && !hostname.startsWith('*.')) {
                    modal.querySelector('#edit_manual_subdomain').value = parts.slice(0, -2).join('.');
                    modal.querySelector('#edit_manual_domain_name').value = parts.slice(-2).join('.');
                } else {
                    modal.querySelector('#edit_manual_subdomain').value = '';
                    modal.querySelector('#edit_manual_domain_name').value = hostname;
                }
                const path = details.path || '';
                modal.querySelector('#edit_manual_path_display').value = path.startsWith('/') ? path.substring(1) : path;
                modal.querySelector('#edit_manual_path').value = path;
                const service = details.service || '';
                const serviceParts = service.split('://');
                if (serviceParts.length === 2) {
                    modal.querySelector('#edit_manual_service_type').value = serviceParts[0];
                    modal.querySelector('#edit_manual_service_address').value = serviceParts[1];
                } else if (service.startsWith('http_status:')) {
                    modal.querySelector('#edit_manual_service_type').value = 'http_status';
                    modal.querySelector('#edit_manual_service_address').value = service.split(':')[1];
                }

                const accessGroupSelect = modal.querySelector('#edit_manual_access_group');
                const manualPolicySelect = modal.querySelector('#edit_manual_access_policy_type');

                const selectedGroups = Array.isArray(details.access_group_id)
                    ? details.access_group_id
                    : (details.access_group_id ? [details.access_group_id] : []);

                if (accessGroupSelect) {
                    if (accessGroupSelect.tomselect) {
                        accessGroupSelect.tomselect.clear();
                        if (selectedGroups.length) {
                            accessGroupSelect.tomselect.setValue(selectedGroups, true);
                        }
                    } else {
                        accessGroupSelect.value = selectedGroups.length ? selectedGroups[0] : '';
                    }
                }

                if (manualPolicySelect) {
                    manualPolicySelect.value = details.access_policy_type || 'none';
                    manualPolicySelect.dispatchEvent(new Event('change'));
                }
                if (accessGroupSelect) {
                    accessGroupSelect.dispatchEvent(new Event('change'));
                }

                const authEmailField = modal.querySelector('#edit_manual_auth_email');
                if (authEmailField) authEmailField.value = details.auth_email || '';

                const zoneOverrideField = modal.querySelector('#edit_manual_zone_name_override');
                if (zoneOverrideField) zoneOverrideField.value = '';

                const noTlsVerifyField = modal.querySelector('#edit_manual_no_tls_verify');
                if (noTlsVerifyField) noTlsVerifyField.checked = details.no_tls_verify || false;

                const originServerNameField = modal.querySelector('#edit_manual_origin_server_name');
                if (originServerNameField) originServerNameField.value = details.origin_server_name || '';

                const httpHostHeaderField = modal.querySelector('#edit_manual_http_host_header');
                if (httpHostHeaderField) httpHostHeaderField.value = details.http_host_header || '';

                const http2OriginField = modal.querySelector('#edit_http2_origin');
                if (http2OriginField) http2OriginField.checked = details.http2_origin || false;

                const disableChunkedEncodingField = modal.querySelector('#edit_disable_chunked_encoding');
                if (disableChunkedEncodingField) disableChunkedEncodingField.checked = details.disable_chunked_encoding || false;

                const matchSniToHostField = modal.querySelector('#edit_match_sni_to_host');
                if (matchSniToHostField) matchSniToHostField.checked = details.match_sni_to_host || false;

                const tunnelDisplay = modal.querySelector('#edit_rule_tunnel_value');
                const zoneDisplay = modal.querySelector('#edit_rule_zone_value');
                const agentHint = modal.querySelector('#edit_rule_agent_hint');

                if (tunnelDisplay) {
                    const tunnelId = details.tunnel_id;
                    const tunnelName = details.tunnel_name || (tunnelId ? 'Tunnel' : 'N/A');
                    if (tunnelId) {
                        const shortId = tunnelId.length > 12 ? `${tunnelId.slice(0, 12)}…` : tunnelId;
                        tunnelDisplay.textContent = `${tunnelName} (${shortId})`;
                    } else {
                        tunnelDisplay.textContent = tunnelName;
                    }
                }
                if (zoneDisplay) {
                    zoneDisplay.textContent = details.zone_name || details.zone_id || '—';
                }
                if (agentHint) {
                    agentHint.classList.toggle('hidden', details.source !== 'agent');
                }

                modal.showModal();
            } catch (e) {
                console.error("Error populating edit modal:", e);
                await dfAlert("Could not open the edit dialog due to an error. Please check the console.", 'Error');
            }
        });
    });
}

function fixResourcesAndBase() {
    const currentProtocol = window.location.protocol;
    const currentHost = window.location.host;

    document.querySelectorAll('link[rel="stylesheet"]').forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && href.startsWith('http:') && currentProtocol === 'https:') {
            link.setAttribute('href', href.replace('http:', 'https:'));
        }
    });
    document.querySelectorAll('script[src]').forEach(function(script) {
        const src = script.getAttribute('src');
        if (src && src.startsWith('http:') && currentProtocol === 'https:') {
            script.setAttribute('src', src.replace('http:', 'https:'));
        }
    });
    document.querySelectorAll('link[rel="preconnect"]').forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && href.startsWith('http:') && currentProtocol === 'https:') {
            const urlObj = new URL(href);
            link.setAttribute('href', currentProtocol + '//' + urlObj.host + (urlObj.pathname || '') + (urlObj.search || ''));
        }
    });

    let baseTag = document.querySelector('base');
    if (!baseTag) {
        baseTag = document.createElement('base');
        document.head.insertBefore(baseTag, document.head.firstChild);
    }
    baseTag.href = currentProtocol + '//' + currentHost + '/';

    const origFetch = window.fetch;
    window.fetch = function(url, options) {
        let processedUrl = url;
        if (url && typeof url === 'string') {
            try {
                const urlObj = new URL(url, document.baseURI);
                if (urlObj.host === currentHost && urlObj.protocol !== currentProtocol) {
                    urlObj.protocol = currentProtocol;
                    processedUrl = urlObj.toString();
                }
            } catch (e) {}
        }
        return origFetch.call(this, processedUrl, options);
    };
}

function fetchServicesSnapshot() {
    const url = `${document.baseURI}api/v2/services?t=${Date.now()}`;
    return fetch(url, { headers: buildApiHeaders() })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Snapshot request failed: ${response.status}`);
            }
            return response.json();
        })
        .then(payload => Array.isArray(payload.services) ? payload.services : []);
}

function updateRowFromService(row, service) {
    if (!row || !service) return;
    row.dataset.ruleStatus = service.status || '';
    row.dataset.ruleSource = service.source || '';

    const statusCell = row.querySelector('[data-role="status-cell"]');
    const statusBadge = statusCell ? statusCell.querySelector('.status-badge') : null;
    if (statusBadge) {
        if (service.source === 'manual') {
            statusBadge.textContent = 'Manual';
            statusBadge.className = 'badge badge-info badge-sm status-badge';
        } else {
            const normalizedStatus = (service.status || 'unknown').replace(/_/g, ' ');
            statusBadge.textContent = normalizedStatus;
            let badgeClass = 'badge-success';
            if (service.status && service.status.includes('pending')) {
                badgeClass = 'badge-warning';
            } else if (service.status && service.status.includes('error')) {
                badgeClass = 'badge-error';
            }
            statusBadge.className = `badge ${badgeClass} badge-sm status-badge`;
        }
    }

    const expiresCell = row.querySelector('[data-role="expires-cell"]');
    if (expiresCell) {
        if (service.status === 'pending_deletion' && service.delete_at) {
            let container = expiresCell.querySelector('[data-delete-at]');
            if (!container) {
                expiresCell.innerHTML = '';
                container = document.createElement('div');
                expiresCell.appendChild(container);
            }
            container.setAttribute('data-delete-at', service.delete_at);

            let absoluteSpan = container.querySelector('.absolute-time-display');
            if (!absoluteSpan) {
                absoluteSpan = document.createElement('span');
                absoluteSpan.className = 'absolute-time-display';
                container.appendChild(absoluteSpan);
            }

            let countdownSpan = container.querySelector('.countdown-timer');
            if (!countdownSpan) {
                countdownSpan = document.createElement('span');
                countdownSpan.className = 'countdown-timer block text-xs opacity-80';
                container.appendChild(countdownSpan);
            }
        } else {
            expiresCell.innerHTML = '<span class="text-xs opacity-60">N/A</span>';
        }
    }
}

function removeServiceRow(ruleId) {
    if (!ruleId) return false;
    let removed = false;
    document.querySelectorAll('tr[data-rule-key]').forEach(row => {
        if (row.dataset.ruleKey === ruleId) {
            row.remove();
            removed = true;
        }
    });
    return removed;
}

function applyServicesSnapshot(services) {
    const servicesById = new Map();
    services.forEach(service => {
        if (service && service.id) {
            servicesById.set(service.id, service);
        }
    });

    const rows = Array.from(document.querySelectorAll('tr[data-rule-key]'));
    rows.forEach(row => {
        const key = row.dataset.ruleKey;
        if (!servicesById.has(key)) {
            row.remove();
            return;
        }
        const service = servicesById.get(key);
        updateRowFromService(row, service);
        servicesById.delete(key);
    });

    if (servicesById.size > 0) {
        window.location.reload();
        return;
    }

    updateCountdowns();
}

function scheduleServicesSnapshotRefresh() {
    if (!document.querySelector('tr[data-rule-key]')) {
        return;
    }

    if (servicesSnapshotPromise) {
        servicesSnapshotQueued = true;
        return;
    }

    servicesSnapshotPromise = fetchServicesSnapshot()
        .then(applyServicesSnapshot)
        .catch(error => {
            console.warn('Failed to refresh services snapshot:', error);
        })
        .finally(() => {
            servicesSnapshotPromise = null;
            if (servicesSnapshotQueued) {
                servicesSnapshotQueued = false;
                scheduleServicesSnapshotRefresh();
            }
        });
}

function findRowByRuleKey(ruleId) {
    if (!ruleId) return null;
    const rows = document.querySelectorAll('tr[data-rule-key]');
    for (const row of rows) {
        if (row.dataset.ruleKey === ruleId) {
            return row;
        }
    }
    return null;
}

function handleStructuredStateEvent(message) {
    const eventType = message.type;
    const data = message.data || {};
    const ruleId = data.id;

    switch (eventType) {
        case 'snapshot_refresh':
            scheduleServicesSnapshotRefresh();
            break;
        case 'service_deleted':
            if (!removeServiceRow(ruleId)) {
                scheduleServicesSnapshotRefresh();
            }
            break;
        case 'service_pending_deletion':
        case 'service_updated':
            const targetRow = findRowByRuleKey(ruleId);
            if (targetRow && data) {
                updateRowFromService(targetRow, data);
                updateCountdowns();
            } else {
                scheduleServicesSnapshotRefresh();
            }
            break;
        case 'service_created':
        default:
            scheduleServicesSnapshotRefresh();
            break;
    }
}

function connectStateUpdateSource() {
    if (!window.EventSource) {
        console.error("Browser doesn't support Server-Sent Events. State auto-refresh disabled.");
        return;
    }

    const streamUrl = `${document.baseURI}stream-state-updates`;
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = function(event) {
        if (!event.data) {
            return;
        }

        if (event.data === 'update') {
            scheduleServicesSnapshotRefresh();
            return;
        }

        if (event.data.trim().length === 0) {
            return;
        }

        try {
            const message = JSON.parse(event.data);
            if (message && message.type) {
                handleStructuredStateEvent(message);
            } else {
                scheduleServicesSnapshotRefresh();
            }
        } catch (error) {
            console.warn('Failed to parse state stream payload:', error);
            scheduleServicesSnapshotRefresh();
        }
    };

    eventSource.onerror = function(err) {
        console.error("State update stream connection error. It will be retried automatically by the browser.", err);
        eventSource.close();
                
        setTimeout(connectStateUpdateSource, 5000); // Reconnect after 5 seconds
    };
}

function addLogLine(message, type = 'log') {
    const logOutput = document.getElementById('log-output');
    if (!logOutput) {
        return;
    }
    if (!initialConnectMessageCleared && logOutput.textContent.includes('Connecting to log stream...')) {
        logOutput.textContent = '';
        initialConnectMessageCleared = true;
    }
    const newLogLine = document.createElement('div');
    newLogLine.textContent = message;
    if (type === 'status') newLogLine.classList.add('text-neutral-content', 'opacity-70', 'italic');
    else if (type === 'error') newLogLine.classList.add('text-red-400', 'font-semibold');
    else if (type === 'connected') newLogLine.classList.add('text-green-400');

    const isScrolledToBottom = logOutput.scrollHeight - logOutput.clientHeight <= logOutput.scrollTop + 10;
    logOutput.appendChild(newLogLine);
    while (logOutput.childNodes.length > maxLogLines) {
        logOutput.removeChild(logOutput.firstChild);
    }
    if (isScrolledToBottom) {
        logOutput.scrollTop = logOutput.scrollHeight;
    }
}

function setupLogControls() {
    const enableBtn = document.getElementById('enable-logs-btn');
    const disableBtn = document.getElementById('disable-logs-btn');
    const clearBtn = document.getElementById('clear-logs-btn');
    const logOutput = document.getElementById('log-output');

    if (!enableBtn || !disableBtn || !clearBtn || !logOutput) return;

    enableBtn.addEventListener('click', () => {
        logsEnabled = true;
        logOutput.classList.remove('hidden');
        logOutput.textContent = 'Connecting to log stream...';
        connectEventSource();
        enableBtn.classList.add('hidden');
        disableBtn.classList.remove('hidden');
    });

    disableBtn.addEventListener('click', () => {
        logsEnabled = false;
        disconnectEventSource();
        logOutput.classList.add('hidden');
        enableBtn.classList.remove('hidden');
        disableBtn.classList.add('hidden');
    });

    clearBtn.addEventListener('click', () => {
        if (logOutput) {
            logOutput.textContent = activeLogSource ? 'Log cleared...\n' : 'Click "Enable Logs" to start streaming...';
        }
    });
}

function disconnectEventSource() {
    if (activeLogSource) {
        try {
            activeLogSource.close();
        } catch (e) {
            console.error("Error closing log stream:", e);
        }
        activeLogSource = null;
    }
    if (eventSourceHealthCheck) {
        clearInterval(eventSourceHealthCheck);
        eventSourceHealthCheck = null;
    }
}

function connectEventSource() {
    const logOutput = document.getElementById('log-output');
    if (!logOutput) {
        return;
    }
    if (!window.EventSource) {
        addLogLine("Browser doesn't support Server-Sent Events.", 'error');
        return;
    }
    if (activeLogSource) {
        try {
            activeLogSource.close();
        } catch (e) {
            console.error("Error closing existing log stream:", e);
        }
        activeLogSource = null;
    }

    const streamUrl = `${document.baseURI}stream-logs?t=${Date.now()}`;
    try {
        activeLogSource = new EventSource(streamUrl);
        let connectionTimeout;
        const resetConnectionTimeout = () => {
            if (connectionTimeout) clearTimeout(connectionTimeout);
            connectionTimeout = setTimeout(() => {
                if (activeLogSource) {
                    activeLogSource.close();
                    activeLogSource = null;
                    addLogLine("--- Log stream connection timeout. Reconnecting... ---", 'error');
                    setTimeout(connectEventSource, 2000);
                }
            }, 10000);
        };
        resetConnectionTimeout();

        activeLogSource.onopen = function() {
            if (connectionTimeout) clearTimeout(connectionTimeout);
            addLogLine("--- Log stream connected ---", 'connected');
        };
        activeLogSource.onmessage = function(event) {
            resetConnectionTimeout();
            if (event.data === "heartbeat" || event.data === ": keepalive") {
                return;
            }
            addLogLine(event.data, 'log');
        };

        let retryAttempt = 0;
        activeLogSource.onerror = function(err) {
            if (connectionTimeout) clearTimeout(connectionTimeout);
            if (activeLogSource && activeLogSource.readyState !== EventSource.CLOSED) {
                addLogLine("--- Log stream connection error. Retrying... ---", 'error');
            }
            if (activeLogSource) {
                activeLogSource.close();
                activeLogSource = null;
            }

            if (logsEnabled) {
                retryAttempt++;
                const delay = Math.min(5000 * Math.pow(1.5, Math.min(retryAttempt - 1, 5)), 30000);
                setTimeout(connectEventSource, delay);
            }
        };
    } catch (e) {
        addLogLine(`--- Failed to establish log stream connection: ${e.message} ---`, 'error');
        if (logsEnabled) {
            setTimeout(connectEventSource, 5000);
        }
    }

    if (eventSourceHealthCheck) clearInterval(eventSourceHealthCheck);
    eventSourceHealthCheck = setInterval(() => {
        if (logsEnabled && (!activeLogSource || activeLogSource.readyState === EventSource.CLOSED)) {
            addLogLine("--- Health check: Log stream disconnected. Reconnecting... ---", 'status');
            connectEventSource();
        }
    }, 15000);
}

function formatTimeDifference(diffMillis) {
    const totalSeconds = Math.round(Math.abs(diffMillis / 1000));
    if (totalSeconds < 60) return diffMillis >= 0 ? 'in <1m' : '<1m ago';
    const days = Math.floor(totalSeconds / (3600 * 24));
    const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    let parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0 || (days === 0 && hours === 0)) parts.push(`${minutes}m`);
    const timeString = parts.join(' ');
    return diffMillis >= 0 ? `in ${timeString}` : `${timeString} ago`;
}

function updateCountdowns() {
    document.querySelectorAll('div[data-delete-at]').forEach(div => {
        const deleteAtISO = div.dataset.deleteAt;
        if (!deleteAtISO) return;
        const absoluteTimeSpan = div.querySelector('.absolute-time-display');
        const countdownSpan = div.querySelector('.countdown-timer');
        if (!absoluteTimeSpan || !countdownSpan) return;

        try {
            const targetDate = new Date(deleteAtISO);
            if (isNaN(targetDate.getTime())) throw new Error("Invalid date");

            const now = new Date();
            const diffMs = targetDate - now;
            const diffSeconds = Math.floor(diffMs / 1000);
            
            if (diffMs < 0) {
                
                absoluteTimeSpan.textContent = "Expired";
                countdownSpan.textContent = "";
                absoluteTimeSpan.className = 'absolute-time-display text-error font-bold';
            } else if (diffSeconds < 3600) {
                
                const minutes = Math.floor(diffSeconds / 60);
                const seconds = diffSeconds % 60;
                const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

                absoluteTimeSpan.textContent = `Expires in ${timeStr}`;
                countdownSpan.textContent = "";
                
                if (diffSeconds <= 10) {
                    absoluteTimeSpan.className = 'absolute-time-display text-error font-bold animate-pulse';
                } else if (diffSeconds <= 30) {
                    absoluteTimeSpan.className = 'absolute-time-display text-error font-semibold';
                } else if (diffSeconds <= 120) {
                    absoluteTimeSpan.className = 'absolute-time-display text-warning font-semibold';
                } else {
                    absoluteTimeSpan.className = 'absolute-time-display text-success';
                }
            } else {

                const hours = Math.floor(diffSeconds / 3600);
                const minutes = Math.floor((diffSeconds % 3600) / 60);

                let timeStr = '';
                if (hours > 0) {
                    timeStr = minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
                } else {
                    timeStr = `${minutes}m`;
                }

                absoluteTimeSpan.textContent = `Expires in ${timeStr}`;
                countdownSpan.textContent = "";
                absoluteTimeSpan.className = 'absolute-time-display text-base-content opacity-70';
            }

            const fullTimestamp = targetDate.toLocaleString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                day: '2-digit',
                month: 'short',
                year: 'numeric'
            });
            div.setAttribute('title', `Exact time: ${fullTimestamp}`);

        } catch (e) {
            absoluteTimeSpan.textContent = "(Invalid Date)";
            countdownSpan.textContent = "";
            console.error("Error processing date for countdown:", deleteAtISO, e);
        }
    });
}

function startServerPing() {
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
        fetch(`${document.baseURI}ping?t=${Date.now()}`)
            .then(response => response.ok ? response.json() : Promise.reject(`Ping failed: ${response.status}`))
            .then(data => {})
            .catch(error => console.warn("Server ping failed:", error));
    }, 30000);
}

function updateReconciliationStatus() {
    fetch(`${document.baseURI}reconciliation-status?t=${Date.now()}`)
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('reconciliation-status');
            const messageElement = document.getElementById('reconciliation-status-message');
            if (!statusElement || !messageElement) return;

            if (data.status) {
                messageElement.textContent = data.status;
                messageElement.style.display = data.in_progress ? 'block' : 'none';
            }
            if (data.in_progress) {
                statusElement.innerHTML = `<div role="alert" class="alert alert-warning shadow-md text-sm"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6 animate-spin"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6l4 2M21.56 10.5A10.001 10.001 0 0012 2a10 10 0 100 20 9.974 9.974 0 005.201-1.71l-.001-.001z"></path></svg><div><h3 class="font-bold">Reconciliation: ${data.progress}%</h3><div class="text-xs">Processing ${data.processed_items} of ${data.total_items} items...</div></div></div>`;
            } else {
                if (statusElement.innerHTML.includes('Reconciliation:')) {
                    statusElement.innerHTML = `<div role="alert" class="alert alert-success shadow-md text-sm"><svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span>Reconciliation complete</span></div>`;
                    setTimeout(() => {
                        if (statusElement.innerHTML.includes('Reconciliation complete')) {
                            statusElement.innerHTML = '';
                            if (messageElement) messageElement.style.display = 'none';
                        }
                    }, 5000);
                }
            }
        }).catch(err => console.warn("Failed to fetch reconciliation status:", err));
}

function setupPathInput(displayElement, hiddenElement) {
    if (!displayElement || !hiddenElement) return;
    displayElement.addEventListener('input', function() {
        let displayValue = this.value.trim();
        if (displayValue) {
            let pathSegment = displayValue.replace(/^\/+/, '');
            hiddenElement.value = '/' + pathSegment;
        } else {
            hiddenElement.value = '';
        }
    });
}

function buildManualHostname(subdomain, domain) {
    const domainPart = (domain || '').trim();
    const subdomainPart = (subdomain || '').trim();
    if (!domainPart) return '';
    return subdomainPart ? `${subdomainPart}.${domainPart}` : domainPart;
}

async function fetchAccountTunnels() {
    if (cachedTunnels !== null) return cachedTunnels;
    try {
        const response = await fetch('/api/v2/tunnels/account', {
            headers: buildApiHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        cachedTunnels = Array.isArray(data.tunnels) ? data.tunnels : [];
    } catch (error) {
        console.error('Failed to load account tunnels', error);
        cachedTunnels = [];
    }
    return cachedTunnels;
}

async function fetchAccountZones() {
    if (cachedZones !== null) return cachedZones;
    try {
        const response = await fetch('/api/v2/zones', {
            headers: buildApiHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        cachedZones = Array.isArray(data) ? data : [];
    } catch (error) {
        console.error('Failed to load account zones', error);
        cachedZones = [];
    }
    return cachedZones;
}

function getZoneById(zoneId) {
    if (!Array.isArray(cachedZones)) return null;
    return cachedZones.find(zone => zone && zone.id === zoneId) || null;
}

function detectZoneForHostname(hostname) {
    if (!hostname) return { status: 'empty' };
    if (!Array.isArray(cachedZones) || cachedZones.length === 0) {
        return { status: 'not_found', candidates: [] };
    }
    let normalizedHost = hostname.toLowerCase();
    if (normalizedHost.startsWith('*.')) {
        normalizedHost = normalizedHost.slice(2);
    }
    const matches = [];
    cachedZones.forEach(zone => {
        const zoneName = (zone && zone.name ? zone.name : '').toLowerCase();
        if (!zoneName) return;
        if (normalizedHost === zoneName || normalizedHost.endsWith(`.${zoneName}`)) {
            matches.push(zone);
        }
    });
    if (matches.length === 0) {
        return { status: 'not_found', candidates: [] };
    }
    const longestLength = Math.max(...matches.map(z => (z.name || '').length));
    const topMatches = matches.filter(z => (z.name || '').length === longestLength);
    if (topMatches.length === 1) {
        return { status: 'ok', zone: topMatches[0] };
    }
    return { status: 'ambiguous', candidates: topMatches };
}

function populateZoneSelector(selector, zones, placeholderText = 'Select a zone...') {
    if (!selector) return;
    selector.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = placeholderText;
    placeholder.disabled = true;
    placeholder.selected = true;
    selector.appendChild(placeholder);
    (zones || []).forEach(zone => {
        if (!zone || !zone.id) return;
        const option = document.createElement('option');
        option.value = zone.id;
        option.textContent = zone.name ? `${zone.name} (${zone.id.slice(0, 8)}${zone.id.length > 8 ? '…' : ''})` : zone.id;
        selector.appendChild(option);
    });
}

function setZoneBadge(badgeEl, text, variant) {
    if (!badgeEl) return;
    badgeEl.textContent = text;
    badgeEl.classList.remove('hidden', 'badge-success', 'badge-warning', 'badge-error', 'badge-info');
    const variantClass = variant ? `badge-${variant}` : 'badge-info';
    badgeEl.classList.add(variantClass);
    badgeEl.classList.remove('hidden');
}

function updateManualZoneUI(state, elements) {
    if (!elements) return;
    const { zoneIdInput, selectorWrapper, selectorEl, messageEl, badgeEl } = elements;
    if (!zoneIdInput || !messageEl) return;

    const hideBadge = () => {
        if (badgeEl) {
            badgeEl.classList.add('hidden');
        }
    };

    switch (state.status) {
        case 'empty':
            zoneIdInput.value = '';
            if (selectorWrapper) selectorWrapper.classList.add('hidden');
            hideBadge();
            messageEl.textContent = 'Enter a hostname to auto-detect the Cloudflare zone.';
            break;
        case 'override':
            zoneIdInput.value = '';
            if (selectorWrapper) selectorWrapper.classList.add('hidden');
            if (state.zoneName) {
                setZoneBadge(badgeEl, 'Override', 'info');
                messageEl.textContent = `Using zone override: ${state.zoneName}`;
            } else {
                hideBadge();
                messageEl.textContent = 'Using zone override.';
            }
            break;
        case 'ok':
            zoneIdInput.value = state.zone && state.zone.id ? state.zone.id : '';
            if (selectorWrapper) selectorWrapper.classList.add('hidden');
            setZoneBadge(badgeEl, 'Detected', 'success');
            messageEl.textContent = state.zone && state.zone.name ? `Detected zone: ${state.zone.name}` : 'Detected zone from hostname.';
            break;
        case 'ambiguous':
            zoneIdInput.value = '';
            if (selectorWrapper && selectorEl) {
                populateZoneSelector(selectorEl, state.candidates, 'Select a matching zone...');
                selectorWrapper.classList.remove('hidden');
            }
            setZoneBadge(badgeEl, 'Select zone', 'warning');
            messageEl.textContent = 'Multiple zones match this hostname. Choose the correct zone below.';
            break;
        case 'not_found':
            zoneIdInput.value = '';
            if (selectorWrapper && selectorEl) {
                populateZoneSelector(selectorEl, cachedZones || [], 'Select a zone...');
                selectorWrapper.classList.remove('hidden');
            }
            setZoneBadge(badgeEl, 'Zone required', 'warning');
            messageEl.textContent = 'No zone matched this hostname. Select the appropriate zone manually.';
            break;
        case 'selected':
            zoneIdInput.value = state.zone && state.zone.id ? state.zone.id : '';
            if (selectorWrapper) selectorWrapper.classList.remove('hidden');
            setZoneBadge(badgeEl, 'Selected', 'success');
            messageEl.textContent = state.zone && state.zone.name ? `Zone selected: ${state.zone.name}` : 'Zone selected.';
            break;
        default:
            break;
    }
}

async function populateManualTunnelOptions(feedbackEl) {
    if (!manualTunnelTomSelect) return;
    const tunnels = await fetchAccountTunnels();
    manualTunnelTomSelect.clearOptions();
    if (Array.isArray(tunnels) && tunnels.length > 0) {
        tunnels.forEach(tunnel => {
            if (!tunnel || !tunnel.id) return;
            const label = tunnel.name ? `${tunnel.name} (${tunnel.id.slice(0, 8)}${tunnel.id.length > 8 ? '…' : ''})` : tunnel.id;
            manualTunnelTomSelect.addOption({ value: tunnel.id, text: label });
        });
        manualTunnelTomSelect.refreshOptions(false);
        const defaultId = manualTunnelTomSelect.input.dataset.defaultTunnelId;
        if (defaultId && tunnels.some(t => t && t.id === defaultId)) {
            manualTunnelTomSelect.setValue(defaultId, true);
        } else {
            manualTunnelTomSelect.clear(true);
        }
        if (feedbackEl) {
            feedbackEl.classList.add('hidden');
            feedbackEl.classList.remove('alert-warning', 'alert-error', 'alert-success');
        }
    } else {
        manualTunnelTomSelect.refreshOptions(false);
        if (feedbackEl) {
            feedbackEl.textContent = 'No tunnels were found for this account. Configure a Cloudflare Tunnel before adding rules.';
            feedbackEl.classList.remove('hidden');
            feedbackEl.classList.remove('alert-success', 'alert-error');
            feedbackEl.classList.add('alert-warning');
        }
    }
}

async function initializeManualRuleForm() {
    const form = document.getElementById('add_manual_rule_form');
    if (!form) return;

    const subdomainInput = document.getElementById('manual_subdomain');
    const domainInput = document.getElementById('manual_domain_name');
    const zoneIdInput = document.getElementById('manual_zone_id');
    const zoneMessageEl = document.getElementById('manual_zone_message');
    const zoneBadgeEl = document.getElementById('manual_zone_status_badge');
    const zoneSelectorWrapper = document.getElementById('manual_zone_selector_wrapper');
    const zoneSelectorEl = document.getElementById('manual_zone_selector');
    const zoneOverrideInput = document.getElementById('manual_zone_name_override');
    const feedbackEl = document.getElementById('manual_rule_feedback');

    const elements = {
        zoneIdInput,
        selectorWrapper: zoneSelectorWrapper,
        selectorEl: zoneSelectorEl,
        messageEl: zoneMessageEl,
        badgeEl: zoneBadgeEl
    };

    await populateManualTunnelOptions(feedbackEl);
    await fetchAccountZones();

    const triggerDetection = async () => {
        const overrideValue = zoneOverrideInput ? zoneOverrideInput.value.trim() : '';
        if (overrideValue) {
            updateManualZoneUI({ status: 'override', zoneName: overrideValue }, elements);
            return;
        }
        const hostname = buildManualHostname(subdomainInput ? subdomainInput.value : '', domainInput ? domainInput.value : '');
        if (!hostname) {
            updateManualZoneUI({ status: 'empty' }, elements);
            return;
        }
        const detectionResult = detectZoneForHostname(hostname);
        updateManualZoneUI(detectionResult, elements);
    };

    const scheduleDetection = () => {
        if (manualZoneDetectionTimeout) {
            clearTimeout(manualZoneDetectionTimeout);
        }
        manualZoneDetectionTimeout = setTimeout(triggerDetection, 200);
    };

    if (subdomainInput) subdomainInput.addEventListener('input', scheduleDetection);
    if (domainInput) domainInput.addEventListener('input', scheduleDetection);

    if (zoneOverrideInput) {
        zoneOverrideInput.addEventListener('input', () => {
            if (zoneOverrideInput.value.trim()) {
                updateManualZoneUI({ status: 'override', zoneName: zoneOverrideInput.value.trim() }, elements);
            } else {
                scheduleDetection();
            }
        });
    }

    if (zoneSelectorEl) {
        zoneSelectorEl.addEventListener('change', () => {
            const selectedId = zoneSelectorEl.value;
            if (!selectedId) {
                zoneIdInput.value = '';
                return;
            }
            const zone = getZoneById(selectedId) || { id: selectedId };
            updateManualZoneUI({ status: 'selected', zone }, elements);
        });
    }

    scheduleDetection();
}

function openCreateAccessGroupModal() {
    const modal = document.getElementById('access_group_modal');
    if (!modal) return;
    const form = document.getElementById('access_group_form');
    const title = document.getElementById('access_group_modal_title');
    const groupIdInput = document.getElementById('group_id');

    form.reset();
    form.action = `${document.baseURI}ui/access-groups/create`;
    title.textContent = 'Create New Access Group';
    groupIdInput.disabled = false;
    document.getElementById('original_group_id').value = '';

    const countrySelect = document.getElementById('group_countries');
    if (countrySelect && countrySelect.tomselect) {
        countrySelect.tomselect.clear();
        countrySelect.tomselect.sync();
        if (window.enhancedCountrySelector && window.enhancedCountrySelector.updateSelectionCounter) {
            window.enhancedCountrySelector.updateSelectionCounter();
        }
    }

    if (window.idpTomSelect) {
        window.idpTomSelect.clear();
    }

    modal.showModal();
}

async function openEditAccessGroupModal(groupId, details) {
    const modal = document.getElementById('access_group_modal');
    if (!modal) return;
    const form = document.getElementById('access_group_form');
    const title = document.getElementById('access_group_modal_title');
    const groupIdInput = document.getElementById('group_id');

    form.reset();
    form.action = `${document.baseURI}ui/access-groups/edit/${encodeURIComponent(groupId)}`;
    title.textContent = `Edit Access Group: ${details.display_name}`;

    document.getElementById('original_group_id').value = groupId;
    groupIdInput.value = groupId;
    groupIdInput.disabled = true;

    document.getElementById('group_display_name').value = details.display_name || '';
    document.getElementById('group_session_duration').value = details.session_duration || '24h';
    document.getElementById('group_app_launcher_visible').checked = details.app_launcher_visible || false;
    document.getElementById('group_auto_redirect').checked = details.auto_redirect_to_identity || false;

    const isPublicMode = details.public_mode === true;
    document.getElementById('public_mode').value = isPublicMode ? 'true' : 'false';

    if (typeof window.switchToMode === 'function') {
        if (isPublicMode) {
            window.switchToMode('public');
        } else {
            window.switchToMode('authenticated');
        }
    }

    let emailText = '';
    let ipRangeText = '';
    let selectedCountries = [];
    let selectedIdpIds = [];

    if (details.policies && Array.isArray(details.policies)) {
        const emails = [];
        const ipRanges = [];

        details.policies.forEach(policy => {
            if (policy.include) {
                policy.include.forEach(rule => {
                    if (rule.email && rule.email.email) emails.push(rule.email.email);
                    else if (rule.email_domain && rule.email_domain.domain) emails.push(`@${rule.email_domain.domain}`);
                    else if (rule.ip && rule.ip.ip) ipRanges.push(rule.ip.ip);
                    else if (rule['login_method'] && rule['login_method'].id) selectedIdpIds.push(rule['login_method'].id);
                });
            }

            if (policy.exclude && Array.isArray(policy.exclude)) {
                policy.exclude.forEach(rule => {
                    if (rule.geo && rule.geo.country_code) {
                        selectedCountries.push(rule.geo.country_code);
                    }
                });
            }
        });

        emailText = [...new Set(emails)].join(', ');
        ipRangeText = [...new Set(ipRanges)].join(', ');
        selectedCountries = [...new Set(selectedCountries)];
    }

    document.getElementById('group_emails').value = emailText;
    document.getElementById('group_ip_ranges').value = ipRangeText;

    const countrySelect = document.getElementById('group_countries');
    if (countrySelect && countrySelect.tomselect) {
        countrySelect.tomselect.setValue(selectedCountries);
        if (window.enhancedCountrySelector && window.enhancedCountrySelector.updateSelectionCounter) {
            window.enhancedCountrySelector.updateSelectionCounter();
        }
    } else if (countrySelect) {
        Array.from(countrySelect.options).forEach(option => {
            option.selected = selectedCountries.includes(option.value);
        });
    }

    if (window.idpTomSelect && selectedIdpIds.length > 0) {
        try {
            const response = await fetch('/api/v2/idp/list');
            const data = await response.json();

            if (data.success && data.identity_providers) {
                const idToFriendlyName = {};
                for (const [friendlyName, idpData] of Object.entries(data.identity_providers)) {
                    idToFriendlyName[idpData.cloudflare_id] = friendlyName;
                }

                const selectedIdpFriendlyNames = selectedIdpIds
                    .map(id => idToFriendlyName[id])
                    .filter(name => name);

                window.idpTomSelect.setValue(selectedIdpFriendlyNames);
            }
        } catch (err) {
            console.error('Failed to load IdPs for edit modal:', err);
        }
    }

    modal.showModal();
}

function updateManualRuleServiceFields() {
    const manualServiceTypeSelect = document.getElementById('manual_service_type');
    if (!manualServiceTypeSelect) return;
    
    const selectedType = manualServiceTypeSelect.value.toLowerCase();
    const noTlsVerifyDiv = document.getElementById('manual_no_tls_verify_div');
    const originServerNameDiv = document.getElementById('manual_origin_server_name_div');
    const manualServiceAddressInput = document.getElementById('manual_service_address');
    const manualServiceAddressLabel = document.getElementById('manual_service_address_label');
    const manualServiceHelpText = document.getElementById('manual_service_help');
    const manualServicePrefixSpan = document.getElementById('manual_service_prefix_span');
    const matchSniToHostDiv = document.getElementById('manual_match_sni_to_host_div');
    let showNoTlsVerify = false;
    let showOriginServerName = false;

    if (manualServiceAddressInput) manualServiceAddressInput.style.display = '';
    if (manualServicePrefixSpan) manualServicePrefixSpan.classList.add('hidden');
    if (manualServiceAddressInput) manualServiceAddressInput.placeholder = 'host:port or status code';
    if (manualServiceAddressLabel) manualServiceAddressLabel.textContent = 'URL (Required for most types)';
    if (manualServiceHelpText) manualServiceHelpText.textContent = 'e.g., 192.168.1.10:8000 or my-service.local:3000 for HTTP/S/TCP etc.';

    if (selectedType === 'http' || selectedType === 'https') {
        if (manualServicePrefixSpan) {
            manualServicePrefixSpan.textContent = selectedType + '://';
            manualServicePrefixSpan.classList.remove('hidden');
        }
        if (manualServiceAddressInput) manualServiceAddressInput.placeholder = 'host:port or resolvable hostname';
        if (manualServiceAddressLabel) manualServiceAddressLabel.textContent = 'Origin URL (Required)';
        if (manualServiceHelpText) manualServiceHelpText.textContent = 'e.g., 192.168.1.10:8000 or my-service.local:3000';
        showNoTlsVerify = true;
        showOriginServerName = true;
    } else if (selectedType === 'tcp' || selectedType === 'ssh' || selectedType === 'rdp') {
        if (manualServicePrefixSpan) {
            manualServicePrefixSpan.textContent = selectedType + '://';
            manualServicePrefixSpan.classList.remove('hidden');
        }
        if (manualServiceAddressInput) manualServiceAddressInput.placeholder = 'host:port';
        if (manualServiceAddressLabel) manualServiceAddressLabel.textContent = `Origin Address for ${selectedType.toUpperCase()} (host:port)`;
        if (manualServiceHelpText) manualServiceHelpText.textContent = `e.g., my-internal-server:22`;
    } else if (selectedType === 'http_status') {
        if (manualServiceAddressInput) manualServiceAddressInput.placeholder = 'e.g., 404';
        if (manualServiceAddressLabel) manualServiceAddressLabel.textContent = 'HTTP Status Code (e.g., 200, 404, 503)';
        if (manualServiceHelpText) manualServiceHelpText.textContent = 'Enter a valid HTTP status code (100-599).';    
    } else if (selectedType === 'bastion') {
        if (manualServiceAddressInput) manualServiceAddressInput.style.display = 'none';
        if (manualServicePrefixSpan) manualServicePrefixSpan.classList.add('hidden');
        if (manualServiceAddressLabel) manualServiceAddressLabel.textContent = 'Origin URL (Not Required)';
        if (manualServiceHelpText) manualServiceHelpText.textContent = 'Bastion mode routes based on the public hostname directly.';
        showNoTlsVerify = false;
        showOriginServerName = false;
    }

    if (noTlsVerifyDiv) {
        noTlsVerifyDiv.style.display = showNoTlsVerify ? '' : 'none';
    }
    if (originServerNameDiv) {
        originServerNameDiv.style.display = showOriginServerName ? '' : 'none';
    }
    if (matchSniToHostDiv) {
        matchSniToHostDiv.style.display = showOriginServerName ? '' : 'none';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    fixResourcesAndBase();
    themeManager.initialize();
    initializeAllTomSelects();
      
    const manualServiceTypeSelect = document.getElementById('manual_service_type');
    if (manualServiceTypeSelect) {
        manualServiceTypeSelect.addEventListener('change', updateManualRuleServiceFields);
        updateManualRuleServiceFields(); // Run once on load
        setupPathInput(document.getElementById('manual_path_display'), document.getElementById('manual_path'));
        setupPathInput(document.getElementById('edit_manual_path_display'), document.getElementById('edit_manual_path'));
        initializeEditRuleModal();
        initializeManualRuleForm();
    }

    const deleteTunnelModal = document.getElementById('delete_tunnel_modal');
    if (deleteTunnelModal) {
        const confirmInput = document.getElementById('delete_tunnel_confirm_input');
        const confirmButton = document.getElementById('delete_tunnel_confirm_button');
        const tunnelIdField = document.getElementById('delete_tunnel_id');
        const warningText = document.getElementById('delete_tunnel_warning_text');

        const updateConfirmState = () => {
            if (!confirmButton) return;
            confirmButton.disabled = confirmInput.value.trim().toLowerCase() !== 'delete';
        };

        if (confirmInput) {
            confirmInput.addEventListener('input', updateConfirmState);
        }

        document.querySelectorAll('.delete-tunnel-btn').forEach(button => {
            button.addEventListener('click', () => {
                const tunnelId = button.dataset.tunnelId || '';
                const tunnelName = button.dataset.tunnelName || '';
                const friendlyName = tunnelName || tunnelId;
                const safeName = friendlyName
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
                if (tunnelIdField) {
                    tunnelIdField.value = tunnelId;
                }
                if (warningText) {
                    warningText.innerHTML = `Deleting <span class="font-semibold">${safeName}</span> will disconnect any agents currently connected to this Cloudflare Tunnel. This action cannot be undone.`;
                }
                if (confirmInput) {
                    confirmInput.value = '';
                    updateConfirmState();
                }
                deleteTunnelModal.showModal();
            });
        });
    }
    
    const manualAccessGroupSelect = document.getElementById('manual_access_group');
    const manualPolicyOptionsWrapper = document.getElementById('manual_policy_options_wrapper');
    if (manualAccessGroupSelect && manualPolicyOptionsWrapper) {
        manualAccessGroupSelect.addEventListener('change', function() {
            const isDisabled = !!this.value;
            manualPolicyOptionsWrapper.style.opacity = isDisabled ? '0.5' : '1';
            manualPolicyOptionsWrapper.querySelectorAll('select, input').forEach(el => {
                el.disabled = isDisabled;
            });
        });
        manualAccessGroupSelect.dispatchEvent(new Event('change'));
    }
    
    const editManualAccessGroupSelect = document.getElementById('edit_manual_access_group');
    const editManualPolicyOptionsWrapper = document.getElementById('edit_manual_policy_options_wrapper');
    if (editManualAccessGroupSelect && editManualPolicyOptionsWrapper) {
        editManualAccessGroupSelect.addEventListener('change', function() {
            const isDisabled = !!this.value;
            editManualPolicyOptionsWrapper.style.opacity = isDisabled ? '0.5' : '1';
            editManualPolicyOptionsWrapper.querySelectorAll('select, input').forEach(el => {
                el.disabled = isDisabled;
            });
        });
    }
  
    document.querySelectorAll('.policy-type-select').forEach(select => {


        const container = select.closest('.dropdown-content, .modal-box, form');
        if (!container) {
            console.warn('Could not find container for policy select:', select);
            return;
        }

        const emailField = container.querySelector('.auth-email-field');
        if (!emailField) {
            
            return;
        }

        const toggleEmailField = () => {
            if (select.value === 'authenticate_email') {
                emailField.classList.remove('hidden');
            } else {
                emailField.classList.add('hidden');
            }
        };

        const clearAccessGroupOnPolicyChange = () => {
            if (select.value && select.value !== 'none') {
                const accessGroupSelect = container.querySelector('#manual_access_group, #edit_manual_access_group');
                if (accessGroupSelect) {
                    if (accessGroupSelect.tomselect) {
                        accessGroupSelect.tomselect.clear();
                    } else {
                        accessGroupSelect.value = '';
                    }
                    accessGroupSelect.dispatchEvent(new Event('change'));
                }
            }
        };
        
        select.addEventListener('change', () => {
            toggleEmailField();
            clearAccessGroupOnPolicyChange();
        });
    
    });

    document.querySelectorAll('.tunnel-dns-toggle').forEach(button => {
        button.addEventListener('click', async function() {
            const tunnelId = this.dataset.tunnelId;
            const dnsRecordsDisplayRow = this.closest('tr').nextElementSibling;
            const targetDiv = document.getElementById(this.getAttribute('aria-controls'));
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            const expandIcon = this.querySelector('.expand-icon');
            const collapseIcon = this.querySelector('.collapse-icon');

            if (!dnsRecordsDisplayRow || !targetDiv) return;

            if (isExpanded) {
                dnsRecordsDisplayRow.classList.add('hidden');
                this.setAttribute('aria-expanded', 'false');
                if (expandIcon) expandIcon.classList.remove('hidden');
                if (collapseIcon) collapseIcon.classList.add('hidden');
            } else {
                this.setAttribute('aria-expanded', 'true');
                if (expandIcon) expandIcon.classList.add('hidden');
                if (collapseIcon) collapseIcon.classList.remove('hidden');

                if (targetDiv.dataset.loaded !== 'true' || targetDiv.dataset.loaded === 'error') {
                    targetDiv.innerHTML = '<p class="opacity-60 italic animate-pulse p-2">Loading DNS records...</p>';
                    dnsRecordsDisplayRow.classList.remove('hidden');

                    try {
                        const fetchUrl = `${document.baseURI}tunnel-dns-records/${encodeURIComponent(tunnelId)}?t=${Date.now()}`;
                        const response = await fetch(fetchUrl);
                        if (!response.ok) {
                            let errorDetail = `HTTP error ${response.status}`;
                            try { const errorData = await response.json(); errorDetail = errorData.error || errorData.message || errorDetail; } catch (e) {}
                            throw new Error(errorDetail);
                        }
                        const data = await response.json();
                        const currentTargetDiv = document.getElementById(`dns-records-${tunnelId}`);
                        if (!currentTargetDiv) return;

                        if (data.dns_records && data.dns_records.length > 0) {
                            let dnsHtml = '<ul class="list-none pl-4 space-y-1.5">';
                            data.dns_records.forEach(record => {
                                const recordUrl = `https://${record.name}`;
                                const zoneDisplay = record.zone_name ? record.zone_name : record.zone_id;
                                dnsHtml += `<li class="opacity-90 text-xs"><svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 inline-block mr-1 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg> <a href="${recordUrl}" target="_blank" rel="noopener noreferrer" class="link link-hover">${record.name}</a> <span class="ml-2 opacity-60">(Zone: ${zoneDisplay})</span></li>`;
                            });
                            dnsHtml += '</ul>';
                            currentTargetDiv.innerHTML = dnsHtml;
                            currentTargetDiv.dataset.loaded = 'true';
                        } else {
                            currentTargetDiv.innerHTML = `<p class="opacity-60 italic p-2">${data.message || 'No CNAME records found.'}</p>`;
                            currentTargetDiv.dataset.loaded = 'true';
                        }
                    } catch (error) {
                        const errorTargetDiv = document.getElementById(`dns-records-${tunnelId}`);
                        if (errorTargetDiv) {
                            errorTargetDiv.innerHTML = `<p class="text-error p-2">Error loading DNS records: ${error.message}</p>`;
                            errorTargetDiv.dataset.loaded = 'error';
                        }
                    }
                }
                dnsRecordsDisplayRow.classList.remove('hidden');
            }
        });
    });
    
    document.querySelectorAll('.edit-access-group-btn').forEach(button => {
        button.addEventListener('click', function() {
            const groupId = this.dataset.groupId;
            const details = JSON.parse(this.dataset.groupDetails);
            openEditAccessGroupModal(groupId, details);
        });
    });

    const createAccessGroupBtn = document.getElementById('create-access-group-btn');
    if (createAccessGroupBtn) {
        createAccessGroupBtn.addEventListener('click', function() {
            openCreateAccessGroupModal();
        });
    }
    
    document.querySelectorAll('form.protocol-aware-form').forEach(form => {
        if (form.getAttribute('action')) {
            try {
                const fullActionUrl = new URL(form.getAttribute('action'), document.baseURI);
                form.setAttribute('action', fullActionUrl.toString());
            } catch (e) {}
        }
    });

    
    updateCountdowns();
    setInterval(updateCountdowns, 1000); 

    
    if (document.getElementById('log-output')) {
        setupLogControls();
    }
    
    if (document.getElementById('reconciliation-status')) {
       
        updateReconciliationStatus();
        setInterval(updateReconciliationStatus, 2000);
    }

    connectStateUpdateSource();
    scheduleServicesSnapshotRefresh();

    startServerPing();

    if (document.getElementById('idp-table-container')) {
        loadIdentityProviders();

        document.getElementById('sync-idps-btn')?.addEventListener('click', syncIdentityProviders);
        document.getElementById('create-idp-btn')?.addEventListener('click', () => {
            showIdPModal('create');
        });

        document.getElementById('idp-form')?.addEventListener('submit', handleIdPFormSubmit);
        document.getElementById('idp-type')?.addEventListener('change', updateIdPFormFields);
    }
    
    window.addEventListener('beforeunload', function() {
        if (activeLogSource) activeLogSource.close();
        if (eventSourceHealthCheck) clearInterval(eventSourceHealthCheck);
        if (pingInterval) clearInterval(pingInterval);
    });
});

let idpTypes = {};

async function loadIdentityProviders() {
    try {
        const [typesResponse, idpsResponse] = await Promise.all([
            fetch('/api/v2/idp/types'),
            fetch('/api/v2/idp/list')
        ]);

        if (typesResponse.ok) {
            const typesData = await typesResponse.json();
            idpTypes = typesData.types || {};
        }

        if (idpsResponse.ok) {
            const data = await idpsResponse.json();
            renderIdPTable(data.identity_providers || {});
        } else {
            document.getElementById('idp-table-container').innerHTML =
                '<p class="text-center text-error py-8">Failed to load identity providers</p>';
        }
    } catch (error) {
        console.error('Error loading IdPs:', error);
        document.getElementById('idp-table-container').innerHTML =
            '<p class="text-center text-error py-8">Error loading identity providers</p>';
    }
}

function renderIdPTable(idps) {
    const container = document.getElementById('idp-table-container');

    if (!idps || Object.keys(idps).length === 0) {
        container.innerHTML = '<p class="text-center opacity-70 py-8">No identity providers configured. Click "Add Provider" to get started.</p>';
        return;
    }

    const typeIcons = {
        'google': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
        'google-apps': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
        'azureAD': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="#00A4EF" d="M0 0h11.377v11.372H0z"/><path fill="#FFB900" d="M12.623 0H24v11.372H12.623z"/><path fill="#7FBA00" d="M0 12.628h11.377V24H0z"/><path fill="#F25022" d="M12.623 12.628H24V24H12.623z"/></svg>',
        'okta': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="#007DC1" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 18c-3.314 0-6-2.686-6-6s2.686-6 6-6 6 2.686 6 6-2.686 6-6 6z"/></svg>',
        'github': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="currentColor" d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>',
        'oidc': '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>',
        'onetimepin': '<svg class="w-6 h-6" viewBox="0 0 32 32"><path d="M8.16 23h21.177v-5.86l-4.023-2.307-.694-.3-16.46.113z" fill="#fff"/><path d="M22.012 22.222c.197-.675.122-1.294-.206-1.754-.3-.422-.807-.666-1.416-.694l-11.545-.15c-.075 0-.14-.038-.178-.094s-.047-.13-.028-.206c.038-.113.15-.197.272-.206l11.648-.15c1.38-.066 2.88-1.182 3.404-2.55l.666-1.735a.38.38 0 0 0 .02-.225c-.75-3.395-3.78-5.927-7.4-5.927-3.34 0-6.17 2.157-7.184 5.15-.657-.488-1.5-.75-2.392-.666-1.604.16-2.9 1.444-3.048 3.048a3.58 3.58 0 0 0 .084 1.191A4.84 4.84 0 0 0 0 22.1c0 .234.02.47.047.703.02.113.113.197.225.197H21.58a.29.29 0 0 0 .272-.206l.16-.572z" fill="#f38020"/><path d="M25.688 14.803l-.32.01c-.075 0-.14.056-.17.13l-.45 1.566c-.197.675-.122 1.294.206 1.754.3.422.807.666 1.416.694l2.457.15c.075 0 .14.038.178.094s.047.14.028.206c-.038.113-.15.197-.272.206l-2.56.15c-1.388.066-2.88 1.182-3.404 2.55l-.188.478c-.038.094.028.188.13.188h8.797a.23.23 0 0 0 .225-.169A6.41 6.41 0 0 0 32 21.106a6.32 6.32 0 0 0-6.312-6.302" fill="#faae40"/></svg>'
    };

    let tableHTML = `
        <table class="table table-zebra table-sm policy-table w-full">
            <colgroup>
                <col class="col-primary">
                <col class="col-secondary">
                <col class="col-tertiary">
                <col class="col-status">
                <col class="col-actions">
            </colgroup>
            <thead>
                <tr>
                    <th class="p-3">Provider</th>
                    <th class="p-3">Cloudflare ID</th>
                    <th class="p-3">Connector</th>
                    <th class="p-3">Status</th>
                    <th class="p-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody>`;

    for (const [friendlyName, idpData] of Object.entries(idps)) {
        const icon = typeIcons[idpData.type] || '<svg class="w-6 h-6" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>';
        const isSystem = idpData.system_managed || false;
        const statusBadge = isSystem ?
            '<span class="badge badge-sm badge-success gap-2"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>System-managed</span>' :
            '<span class="badge badge-sm badge-info gap-2"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>User-configured</span>';

        tableHTML += `
            <tr>
                <td class="p-3">
                    <div class="flex items-center gap-3">
                        <span class="inline-flex items-center justify-center">${icon}</span>
                        <div class="font-medium">${idpData.name}</div>
                    </div>
                </td>
                <td class="p-3 text-xs opacity-70">
                    ${idpData.cloudflare_id ? `<span class="tooltip" data-tip="${idpData.cloudflare_id}"><code>${idpData.cloudflare_id.slice(0, 8)}...</code></span>` : '-'}
                </td>
                <td class="p-3 text-sm opacity-80">${idpData.type}</td>
                <td class="p-3">${statusBadge}</td>
                <td class="p-3 text-right">
                    <div class="dropdown dropdown-end">
                        <label tabindex="0" class="btn btn-ghost btn-sm">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
                            </svg>
                        </label>
                        <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">`;

        if (!isSystem) {
            tableHTML += `
                            <li><a onclick="showIdPModal('edit', '${friendlyName}')">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                                </svg>
                                Edit
                            </a></li>`;
        }

        if (idpData.cloudflare_id) {
            tableHTML += `
                            <li><a onclick="testIdP('${idpData.cloudflare_id}')">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Test IdP
                            </a></li>`;
        }

        if (!isSystem) {
            tableHTML += `
                            <li><a onclick="deleteIdP('${friendlyName}')" class="text-error">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                                </svg>
                                Delete
                            </a></li>`;
        }

        tableHTML += `
                        </ul>
                    </div>
                </td>
            </tr>`;
    }

    tableHTML += `
            </tbody>
        </table>`;

    container.innerHTML = tableHTML;
}

async function syncIdentityProviders() {
    const btn = document.getElementById('sync-idps-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Syncing...';

    try {
        const response = await fetch('/api/v2/idp/sync', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();

        if (data.success) {
            await loadIdentityProviders();
        } else {
            await dfAlert('Error: ' + (data.error || 'Failed to sync identity providers'), 'Sync Error');
        }
    } catch (error) {
        console.error('Error syncing IdPs:', error);
        await dfAlert('Error syncing identity providers. Check console for details.', 'Error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 mr-1"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg> Sync from Cloudflare';
    }
}

function showIdPModal(mode, friendlyName = null) {
    const modal = document.getElementById('idp-modal');
    const form = document.getElementById('idp-form');
    const title = document.getElementById('idp-modal-title');
    const submitBtn = document.getElementById('idp-submit-btn');

    document.getElementById('idp-mode').value = mode;

    form.reset();
    document.getElementById('idp-config-fields').innerHTML = '<div class="alert alert-warning"><svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg><span>Select a provider type to configure credentials</span></div>';

    if (mode === 'create') {
        title.textContent = 'Add Identity Provider';
        submitBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-1"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Create Provider';
        document.getElementById('idp-friendly-name').disabled = false;
    } else if (mode === 'edit' && friendlyName) {
        title.textContent = 'Edit Identity Provider';
        submitBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-1"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Update Provider';
        document.getElementById('idp-friendly-name').disabled = true;
        document.getElementById('idp-edit-name').value = friendlyName;

        fetch(`/api/v2/idp/${friendlyName}`)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.identity_provider) {
                    const idp = data.identity_provider;
                    document.getElementById('idp-friendly-name').value = friendlyName;
                    document.getElementById('idp-display-name').value = idp.name || '';
                    document.getElementById('idp-type').value = idp.type || '';
                    updateIdPFormFields();
                }
            });
    }

    modal.showModal();
}

function updateIdPFormFields() {
    const type = document.getElementById('idp-type').value;
    const container = document.getElementById('idp-config-fields');
    const redirectInfo = document.getElementById('redirect-url-info');

    if (!type || !idpTypes[type]) {
        container.innerHTML = '<div class="alert alert-warning"><svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg><span>Select a provider type to configure credentials</span></div>';
        redirectInfo.classList.add('hidden');
        return;
    }

    const typeConfig = idpTypes[type];
    let fieldsHTML = '';

    for (const [fieldName, fieldConfig] of Object.entries(typeConfig.fields)) {
        const required = fieldConfig.required ? '<span class="label-text-alt text-error">*</span>' : '';
        const inputType = fieldConfig.type === 'password' ? 'password' : 'text';
        const placeholder = fieldConfig.placeholder || '';

        fieldsHTML += `
            <div class="form-control">
                <label class="label">
                    <span class="label-text font-semibold">${fieldConfig.label}</span>
                    ${required}
                </label>
                <input type="${inputType}"
                       id="idp-config-${fieldName}"
                       name="${fieldName}"
                       placeholder="${placeholder}"
                       class="input input-bordered w-full"
                       ${fieldConfig.required ? 'required' : ''}>
            </div>`;
    }

    container.innerHTML = fieldsHTML;

    redirectInfo.classList.remove('hidden');
    document.getElementById('redirect-url-display').textContent = 'https://[your-team].cloudflareaccess.com/cdn-cgi/access/callback';
}

async function handleIdPFormSubmit(e) {
    e.preventDefault();

    const mode = document.getElementById('idp-mode').value;
    const friendlyName = document.getElementById('idp-friendly-name').value.trim();
    const displayName = document.getElementById('idp-display-name').value.trim();
    const type = document.getElementById('idp-type').value;

    const config = {};
    const configFields = document.querySelectorAll('#idp-config-fields input');
    configFields.forEach(input => {
        if (input.name && input.value) {
            config[input.name] = input.value;
        }
    });

    const submitBtn = document.getElementById('idp-submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Saving...';

    try {
        let response;
        if (mode === 'create') {
            response = await fetch('/api/v2/idp/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    friendly_name: friendlyName,
                    name: displayName,
                    type: type,
                    config: config
                })
            });
        } else {
            const editName = document.getElementById('idp-edit-name').value;
            response = await fetch(`/api/v2/idp/${editName}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: displayName,
                    config: config
                })
            });
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('idp-modal').close();
            await loadIdentityProviders();

            if (data.test_url && mode === 'create') {
                const shouldTest = await dfConfirm('Identity provider created successfully!\n\nWould you like to test this identity provider now?', 'Test Identity Provider');
                if (shouldTest) {
                    window.open(data.test_url, '_blank');
                }
            }
        } else {
            await dfAlert('Error: ' + (data.error || 'Failed to save identity provider'), 'Save Error');
        }
    } catch (error) {
        console.error('Error saving IdP:', error);
        await dfAlert('Error saving identity provider. Check console for details.', 'Error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = mode === 'create' ?
            '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-1"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Create Provider' :
            '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-1"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Update Provider';
    }
}

async function testIdP(idpId) {
    try {
        const response = await fetch('/api/v2/idp/list');
        const data = await response.json();

        if (data.success) {
            for (const idp of Object.values(data.identity_providers)) {
                if (idp.cloudflare_id === idpId) {
                    const testUrl = `https://dataverse.cloudflareaccess.com/cdn-cgi/access/test-idp/${idpId}`;
                    window.open(testUrl, '_blank');
                    return;
                }
            }
        }
    } catch (error) {
        console.error('Error testing IdP:', error);
        await dfAlert('Error opening test URL. Check console for details.', 'Error');
    }
}

async function deleteIdP(friendlyName) {
    const confirmed = await dfConfirm(`Are you sure you want to delete the identity provider "${friendlyName}"? This will remove it from both DockFlare and Cloudflare.`, 'Delete Identity Provider');
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/v2/idp/${friendlyName}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            await loadIdentityProviders();
        } else {
            await dfAlert('Error: ' + (data.error || 'Failed to delete identity provider'), 'Delete Error');
        }
    } catch (error) {
        console.error('Error deleting IdP:', error);
        await dfAlert('Error deleting identity provider. Check console for details.', 'Error');
    }
}
