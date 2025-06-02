// src/lib/types/dockflare.ts

// Define types for the nested state objects
export interface TunnelState {
  id?: string | null;
  name?: string;
  status?: 'healthy' | 'degraded' | 'down' | 'unknown' | string; // Add more if needed, or keep string
  token?: string | null;
  status_message?: string;
}

export interface AgentState {
  container_status?: 'running' | 'stopped' | 'starting' | 'error' | 'unknown' | string; // Changed from 'status'
  message?: string; 
  last_action_status?: string; 
}

export interface InitializationStatus {
  complete: boolean;
  in_progress: boolean;
}

export interface RuleValue { 
  service: string;
  path?: string | null;
  hostname_for_dns: string;
  status: 'active' | 'pending_deletion' | 'error' | string;
  delete_at?: string | null; 
  zone_id: string;
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
  all_account_tunnels: any[]; 
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