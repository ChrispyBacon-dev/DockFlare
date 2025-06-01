// src/components/features/dashboard/StatusWidget.tsx
import React from 'react';
import GlassCard from '@/components/ui/GlassCard';

interface StatusWidgetProps {
  title: string;
  value: string | number;
  status?: 'connected' | 'running' | 'disconnected' | 'stopped' | 'error' | 'degraded' | 'unknown' | 'info';
  onClick?: () => void;
  isLoading?: boolean;
  className?: string;
}

const StatusWidget: React.FC<StatusWidgetProps> = ({
  title,
  value,
  status = 'info',
  onClick,
  isLoading = false,
  className = '',
}) => {
  const getStatusColor = () => {
    if (isLoading) return 'text-slate-400';
    switch (status) {
      case 'connected':
      case 'running':
        return 'text-green-400';
      case 'disconnected':
      case 'stopped':
      case 'error':
        return 'text-red-400';
      case 'degraded':
        return 'text-yellow-400';
      case 'unknown':
        return 'text-slate-500';
      default:
        return 'text-cyan-400'; // Default/info color
    }
  };

  return (
    <GlassCard className={`flex flex-col ${className}`} onClick={onClick}>
      <h3 className="text-lg font-semibold text-slate-200 mb-2">{title}</h3>
      {isLoading ? (
        <div className="animate-pulse h-6 bg-slate-600/50 rounded w-3/4"></div>
      ) : (
        <p className={`text-2xl font-bold ${getStatusColor()}`}>{value}</p>
      )}
    </GlassCard>
  );
};

export default StatusWidget;