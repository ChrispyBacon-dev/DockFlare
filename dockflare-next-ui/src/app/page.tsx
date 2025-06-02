// src/app/page.tsx
'use client';

import React from 'react'; 
import useSWR from 'swr'; 
import { 
    DockFlareFullOverview, 
    TunnelState,
    AgentState
} from '@/lib/types'; 
import StatusWidget, { StatusWidgetProps } from '@/components/features/dashboard/StatusWidget';
import GlassCard from '@/components/ui/GlassCard';
import LogViewer from '@/components/features/logs/LogViewer';
import { useRealtimeLogs } from '@/hooks/useRealtimeLogs';
import { fetcher } from '@/lib/fetchers'; 


const Loader = ({ message = "Loading..." }: { message?: string }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full text-slate-400 py-10">
      <svg className="animate-spin h-8 w-8 text-cyan-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      {message}
    </div>
  );
};

const mapTunnelStatus = (liveStatus?: TunnelState['live_status']): StatusWidgetProps['status'] => {
  switch (liveStatus?.toLowerCase()) {
    case 'healthy': return 'connected';
    case 'degraded': return 'degraded';
    case 'down': case 'inactive': return 'disconnected';
    case 'not_found_in_list': case 'id_missing': return 'error'; 
    default: return 'unknown';
  }
};

const mapAgentStatus = (containerStatus?: AgentState['container_status']): StatusWidgetProps['status'] => {
  switch (containerStatus?.toLowerCase()) {
    case 'running': return 'running';
    case 'stopped': return 'stopped';
    case 'starting': return 'starting';
    case 'error': return 'error';
    default: return 'unknown';
  }
};

export default function DashboardPage() {
  const { 
    data: overviewData, 
    error: fetchApiError,     
    isLoading,          
    isValidating        
  } = useSWR<DockFlareFullOverview>(API_OVERVIEW_URL, fetcher, {
    revalidateOnFocus: true,  
  });

  const sseStreamUrl = "/stream-logs";
  const canConnectLogs = !!overviewData && !fetchApiError; 

  const { logs: activityLogs, isConnected: logsConnected } = useRealtimeLogs({ 
    streamUrl: sseStreamUrl,
    autoConnect: canConnectLogs,
  });

  const formatDisplayValue = (value: string | number | undefined | null, defaultValue: string = "N/A"): string => {
    if (value === null || typeof value === 'undefined' || String(value).trim() === "") return defaultValue;
    const strValue = String(value);
    if (['N/A', 'Unknown', 'Error', 'Healthy', 'Degraded', 'Down', 'Running', 'Stopped', 'Starting', 'Connected', 'Disconnected', 'Inactive'].includes(strValue)) {
        return strValue;
    }
    if (typeof value === 'string') {
        return strValue.charAt(0).toUpperCase() + strValue.slice(1);
    }
    return strValue;
  }

  if (isLoading && !overviewData) { 
    return (
        <div className="flex items-center justify-center min-h-[calc(100vh-200px)]"> 
            <Loader message="Loading DockFlare Dashboard..." />
        </div>
    );
  }

  if (fetchApiError && !overviewData) {
    return (
      <GlassCard className="mt-8 text-center !border-red-500/70 p-6">
        <h2 className="text-2xl font-semibold text-red-400 mb-2">Error Loading Dashboard</h2>
        <p className="text-slate-300 mb-4">
          {/* @ts-expect-error (accessing custom properties on error) */}
          {fetchApiError.info?.message || fetchApiError.message || 'An unknown error occurred.'}
        </p>
        {/* SWR automatically retries on error based on its config. 
            A manual retry button could use `mutate(API_OVERVIEW_URL)` if you get `mutate` from useSWR. */}
      </GlassCard>
    );
  }
  
  const tunnelLiveStatus = overviewData?.tunnel_state?.live_status;
  const agentContainerStatus = overviewData?.agent_state?.container_status;
  const managedRulesCount = overviewData?.rules 
    ? Object.keys(overviewData.rules).length 
    : (isLoading || (isValidating && !overviewData) ? "..." : "N/A");

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
          DockFlare Dashboard
        </h1>
        {isValidating && overviewData && (
          <span className="text-xs text-slate-400 animate-pulse">Updating...</span>
        )}
        {fetchApiError && overviewData && (
             <span className="text-xs text-red-400" title={fetchApiError.message}>Failed to update. Displaying cached data.</span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <StatusWidget
          title="Tunnel Status"
          value={(!overviewData && (isLoading || isValidating)) ? "..." : formatDisplayValue(tunnelLiveStatus)}
          status={mapTunnelStatus(tunnelLiveStatus)}
          isLoading={!overviewData && (isLoading || isValidating)} 
        />
        <StatusWidget
          title="Agent Status"
          value={(!overviewData && (isLoading || isValidating)) ? "..." : formatDisplayValue(agentContainerStatus)}
          status={mapAgentStatus(agentContainerStatus)}
          isLoading={!overviewData && (isLoading || isValidating)}
        />
        <StatusWidget
          title="Managed Rules"
          value={String(managedRulesCount)} 
          status="info"
          isLoading={managedRulesCount === "..."}
        />
      </div>

      <div className="h-[350px] sm:h-[400px]">
        <LogViewer 
            logs={activityLogs} 
            isConnected={logsConnected}
            maxHeight="100%"
        />
      </div>
    </div>
  );
}