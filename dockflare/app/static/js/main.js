// app/static/js/main.js - painful .. javascript
const maxLogLines = 250;
let initialConnectMessageCleared = false;
let activeLogSource = null;
let eventSourceHealthCheck = null;
let pingInterval = null;

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
        button.addEventListener('click', function() {
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

                if (details.access_group_id) {
                    accessGroupSelect.value = details.access_group_id;
                } else {
                    accessGroupSelect.value = '';
                }
                
                manualPolicySelect.value = details.access_policy_type || 'none';
                
                accessGroupSelect.dispatchEvent(new Event('change'));
                manualPolicySelect.dispatchEvent(new Event('change'));

                modal.querySelector('#edit_manual_auth_email').value = details.auth_email || '';
                modal.querySelector('#edit_manual_zone_name_override').value = '';
                modal.querySelector('#edit_manual_no_tls_verify').checked = details.no_tls_verify || false;
                modal.querySelector('#edit_manual_origin_server_name').value = details.origin_server_name || '';
                modal.querySelector('#edit_manual_http_host_header').value = details.http_host_header || '';

                modal.showModal();
            } catch (e) {
                console.error("Error populating edit modal:", e);
                alert("Could not open the edit dialog due to an error. Please check the console.");
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

            retryAttempt++;
            const delay = Math.min(5000 * Math.pow(1.5, Math.min(retryAttempt - 1, 5)), 30000);
            setTimeout(connectEventSource, delay);
        };
    } catch (e) {
        addLogLine(`--- Failed to establish log stream connection: ${e.message} ---`, 'error');
        setTimeout(connectEventSource, 5000);
    }

    if (eventSourceHealthCheck) clearInterval(eventSourceHealthCheck);
    eventSourceHealthCheck = setInterval(() => {
        if (!activeLogSource || activeLogSource.readyState === EventSource.CLOSED) {
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
            const options = {
                hour: '2-digit',
                minute: '2-digit',
                day: '2-digit',
                month: 'short',
                year: 'numeric'
            };
            absoluteTimeSpan.textContent = targetDate.toLocaleString(undefined, options);
            const now = new Date();
            const diff = targetDate - now;
            countdownSpan.textContent = `(${formatTimeDifference(diff)})`;
            if (diff < 0) {
                countdownSpan.classList.add('text-error');
                absoluteTimeSpan.classList.add('text-error');
            } else {
                countdownSpan.classList.remove('text-error');
                absoluteTimeSpan.classList.remove('text-error');
            }
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
    
    modal.showModal();
}

function openEditAccessGroupModal(groupId, details) {
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

    let emailText = '';
    if (details.policies) {
        const emails = [];
        details.policies.forEach(policy => {
            if (policy.include) {
                policy.include.forEach(rule => {
                    if (rule.email && rule.email.email) {
                        emails.push(rule.email.email);
                    } else if (rule.email_domain && rule.email_domain.domain) {
                        emails.push(`@${rule.email_domain.domain}`);
                    }
                });
            }
        });
        emailText = emails.join(', ');
    }
    document.getElementById('group_emails').value = emailText;

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
}

document.addEventListener('DOMContentLoaded', function() {
    fixResourcesAndBase();
    themeManager.initialize();
    
    // Setup for Manual Rule Modal (only if on Dashboard Page)
    const manualServiceTypeSelect = document.getElementById('manual_service_type');
    if (manualServiceTypeSelect) {
        manualServiceTypeSelect.addEventListener('change', updateManualRuleServiceFields);
        updateManualRuleServiceFields(); // Run once on load
        setupPathInput(document.getElementById('manual_path_display'), document.getElementById('manual_path'));
        setupPathInput(document.getElementById('edit_manual_path_display'), document.getElementById('edit_manual_path'));
        initializeEditRuleModal();
    }

    // Logic for new Access Group dropdown in ADD Manual Rule Modal
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

    // Logic for new Access Group dropdown in EDIT Manual Rule Modal
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

    // Universal handler for all policy type dropdowns to show/hide the email auth field
    document.querySelectorAll('.policy-type-select').forEach(select => {


        const container = select.closest('.dropdown-content, .modal-box, form');
        if (!container) {
            console.warn('Could not find container for policy select:', select);
            return;
        }

        const emailField = container.querySelector('.auth-email-field');
        if (!emailField) {
            // This is expected for some policy selectors that don't have an email field.
            return;
        }

        const toggleEmailField = () => {
            if (select.value === 'authenticate_email') {
                emailField.classList.remove('hidden');
            } else {
                emailField.classList.add('hidden');
            }
        };

        // Add the event listener for user interactions
        select.addEventListener('change', toggleEmailField);
    
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

    // Setup for Access Group Modal (only if on Access Groups Page)
    document.querySelectorAll('.edit-access-group-btn').forEach(button => {
        button.addEventListener('click', function() {
            const groupId = this.dataset.groupId;
            const details = JSON.parse(this.dataset.groupDetails);
            openEditAccessGroupModal(groupId, details);
        });
    });

    // Universal Form/Link Protocol Correction
    document.querySelectorAll('form.protocol-aware-form').forEach(form => {
        if (form.getAttribute('action')) {
            try {
                const fullActionUrl = new URL(form.getAttribute('action'), document.baseURI);
                form.setAttribute('action', fullActionUrl.toString());
            } catch (e) {}
        }
    });

    // Universal Page Timers and Connections
    updateCountdowns();
    setInterval(updateCountdowns, 30000);

    if (document.getElementById('log-output')) {
        connectEventSource();
    }
    
    if (document.getElementById('reconciliation-status')) {
        updateReconciliationStatus();
        setInterval(updateReconciliationStatus, 2000);
    }
    
    startServerPing();

    // Universal Cleanup
    window.addEventListener('beforeunload', function() {
        if (activeLogSource) activeLogSource.close();
        if (eventSourceHealthCheck) clearInterval(eventSourceHealthCheck);
        if (pingInterval) clearInterval(pingInterval);
    });
});