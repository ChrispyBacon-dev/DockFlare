// dockflare-next-ui/src/lib/types/dockflare.ts

// --- Cloudflare API Specific Types ---
export interface CloudflareTunnelConnection {
  colo_name: string;
  is_pending_reconnect: boolean;
  origin_ip: string;
  opened_at: string; // ISO 8601 datetime string
  uuid: string;
  client_id?: string; // Often present
  client_version?: string; // Often present
}

export interface CloudflareTunnelInfo {
  id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down' | 'pending' | 'inactive' | string; // Added 'inactive' from your backend's mapTunnelStatus
  created_at: string; // ISO 8601 datetime string
  deleted_at?: string | null; // ISO 8601 datetime string
  connections?: CloudflareTunnelConnection[];
  tun_type?: 'cfd_tunnel' | 'warp_connector' | string; // Common types
  // Any other fields you might get from the get_all_account_cloudflare_tunnels() call
}


// --- DockFlare Application Specific Types ---

export interface TunnelState {
  id?: string | null;
  name?: string; // This might be the name of the tunnel DockFlare manages
  status?: 'healthy' | 'degraded' | 'down' | 'unknown' | string; // Current known status from DockFlare's perspective
  token?: string | null; // The tunnel token
  status_message?: string; // More detailed message from DockFlare
  live_status?: 'healthy' | 'degraded' | 'down' | 'inactive' | 'unknown' | 'not_found_in_list' | 'id_missing_for_lookup' | string; // Added from backend logic
}

export interface AgentState {
  container_status?: 'running' | 'stopped' | 'starting' | 'error' | 'unknown' | string;
  message?: string;
  last_action_status?: string;
}

export interface InitializationStatus {
  complete: boolean;
  in_progress: boolean;
}

export interface RuleValue {
  service: string; // e.g., "http://localhost:3000", "tcp://192.168.1.10:22"
  path?: string | null; // e.g., "/grafana"
  hostname_for_dns: string; // e.g., "grafana.example.com"
  container_id?: string | null; // Only for Docker-managed rules
  status: 'active' | 'pending_deletion' | 'error' | string;
  delete_at?: string | null; // ISO 8601 datetime string (from serialize_rule)
  zone_id: string;
  no_tls_verify?: boolean;
  origin_server_name?: string | null;
  access_app_id?: string | null;
  access_policy_type?: 'bypass' | 'authenticate_email' | 'default_tld' | string | null; // Added default_tld
  access_app_config_hash?: string | null;
  auth_email?: string | null;
  access_policy_ui_override?: boolean;
  access_session_duration?: string; 
  access_app_launcher_visible?: boolean;
  access_allowed_idps_str?: string | null; 
  access_auto_redirect?: boolean;
  source: 'docker' | 'manual';
}

export interface ConfigStatus {
  cf_account_id_configured: boolean;
  account_id_for_display: string; 
  cf_zone_id_configured: boolean;
  relevant_zone_name_for_tld_policy?: string | null;
  tld_policy_exists: boolean;
  account_email_for_tld?: string | null;
}

export interface ReconciliationInfo {
  in_progress: boolean;
  progress: number; 
  total_items: number;
  processed_items: number;
  status: string; 
}

export interface DockFlareFullOverview {
  tunnel_state: TunnelState;
  agent_state: AgentState;
  initialization: InitializationStatus;
  display_token?: string | null; 
  cloudflared_container_name: string;
  docker_available: boolean;
  external_cloudflared: boolean;
  external_tunnel_id?: string | null;
  rules: Record<string, RuleValue>; 
  all_account_tunnels: CloudflareTunnelInfo[]; 
  config_status: ConfigStatus;
  reconciliation_info: ReconciliationInfo;
  log_stream_path: string; 
}

export interface DockFlareDashboardDisplayData {
  tunnel_status_display: 'Connected' | 'Disconnected' | 'Degraded' | 'Unknown' | string;
  agent_status_display: 'Running' | 'Stopped' | 'Starting' | 'Error' | 'Unknown' | string;
  managed_rules_count: number;
  last_reconciliation_status_display?: string;
  last_reconciliation_time_display?: string;
}