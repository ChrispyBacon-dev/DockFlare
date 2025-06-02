// dockflare-next-ui/src/lib/types/dockflare.ts

export interface CloudflareTunnelConnection {
  colo_name: string;
  is_pending_reconnect: boolean;
  origin_ip: string;
  opened_at: string; 
  uuid: string;
  client_id?: string; 
  client_version?: string; 
}

export interface CloudflareTunnelInfo {
  id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down' | 'pending' | 'inactive' | string; 
  created_at: string; 
  deleted_at?: string | null; 
  connections?: CloudflareTunnelConnection[];
  tun_type?: 'cfd_tunnel' | 'warp_connector' | string; 
}

export interface TunnelState {
  id?: string | null;
  name?: string; 
  status?: 'healthy' | 'degraded' | 'down' | 'unknown' | string; 
  token?: string | null; 
  status_message?: string; 
  live_status?: 'healthy' | 'degraded' | 'down' | 'inactive' | 'unknown' | 'not_found_in_list' | 'id_missing_for_lookup' | string; 
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

export type AccessPolicyType = 
  | 'none' 
  | 'bypass' 
  | 'authenticate_email' 
  | 'default_tld' 
  | 'authenticate' 
  | 'pending_label_sync'
  | string 
  | null;

export interface RuleValue {
  service: string; 
  path?: string | null; 
  hostname_for_dns: string; 
  container_id?: string | null; 
  status: 'active' | 'pending_deletion' | 'error' | string;
  delete_at?: string | null; 
  zone_id: string;
  no_tls_verify?: boolean;
  origin_server_name?: string | null;
  access_app_id?: string | null;
  access_policy_type?: AccessPolicyType;
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

export interface AccessPolicyPayload {
  access_policy_type: AccessPolicyType; // 'none', 'bypass', 'authenticate_email', 'default_tld'
  auth_email?: string | null; // e.g., "user@example.com, @domain.com"
  session_duration?: string | null; // e.g., "24h"
  app_launcher_visible?: boolean | null;
  allowed_idps_str?: string | null; // Comma-separated UUIDs
  auto_redirect?: boolean | null;
}

export type ServiceType = 
  | 'http' 
  | 'https' 
  | 'tcp' 
  | 'ssh' 
  | 'rdp' 
  | 'http_status' 
  | string; 

export interface ManualRulePayload {
  subdomain?: string | null;
  domain_name: string; 
  path?: string | null; 
  
  service_type: ServiceType; 
  service_address: string; 

  no_tls_verify?: boolean | null;
  origin_server_name?: string | null;
  zone_name_override?: string | null; 

  access_policy_type?: AccessPolicyType;
  auth_email?: string | null;
  access_session_duration?: string | null;
  access_app_launcher_visible?: boolean | null;
  access_allowed_idps_str?: string | null;
  access_auto_redirect?: boolean | null;
}