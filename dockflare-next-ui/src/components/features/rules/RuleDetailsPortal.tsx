// src/components/features/rules/RuleDetailsPortal.tsx
import React from 'react';
import { RuleValue } from '@/lib/types'; 
import GlassCard from '@/components/ui/GlassCard'; 

interface RuleDetailsPortalProps {
  ruleKey: string;
  rule: RuleValue;
  isVisible: boolean;
  position?: { top: number; left: number }; 
}

const RuleDetailsPortal: React.FC<RuleDetailsPortalProps> = ({
  ruleKey,
  rule,
  isVisible,
  position, 
}) => {
  if (!isVisible || !rule) {
    return null;
  }

  const hostname = rule.hostname_for_dns || ruleKey.split('|')[0];

  return (
    <GlassCard 
      className={`
        fixed // Start with fixed positioning for simplicity
        p-4 w-80 md:w-96 z-50  // Give it a size and high z-index
        border-cyan-500/70 shadow-holo-glow-cyan // More prominent glow
        transition-opacity duration-200 ease-in-out
        ${isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}
      `}
      style={position ? { top: `${position.top + 20}px`, left: `${position.left + 20}px` } : { top: '30%', left: '50%', transform: 'translate(-50%, -50%)' }}
    >
      <h3 className="text-lg font-bold text-cyan-300 mb-3 border-b border-cyan-500/30 pb-2">
        Details: {hostname}
      </h3>
      <div className="space-y-1 text-sm text-slate-200">
        <p><strong className="text-slate-400">Full Key:</strong> {ruleKey}</p>
        <p><strong className="text-slate-400">Internal Service:</strong> <span className="font-mono">{rule.service}</span></p>
        <p><strong className="text-slate-400">Path:</strong> {rule.path || '/'}</p>
        <p><strong className="text-slate-400">Source:</strong> {rule.source}</p>
        <p><strong className="text-slate-400">Status:</strong> {rule.status}</p>
        {rule.container_id && <p><strong className="text-slate-400">Container ID:</strong> <span className="text-xs">{rule.container_id}</span></p>}
        {rule.access_policy_type && <p><strong className="text-slate-400">Access Policy:</strong> {rule.access_policy_type}</p>}
        {/* Add more details as needed */}
      </div>
    </GlassCard>
  );
};

export default RuleDetailsPortal;