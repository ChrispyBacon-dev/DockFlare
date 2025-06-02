'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import useSWR from 'swr';
import { DockFlareFullOverview, RuleValue } from '@/lib/types';
import { fetcher } from '@/lib/fetchers';
import { deleteManualRuleApi, forceDeleteRuleApi } from '@/lib/api';
import GlassCard from '@/components/ui/GlassCard';
import BluePortalEffect from '@/components/effects/BluePortalEffect';
import OrangePortalEffect from '@/components/effects/OrangePortalEffect';

const API_OVERVIEW_URL = "/api/v2/overview";

const Loader = ({ message = "Loading rules..." }: { message?: string }) => {
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

const formatRemainingTime = (deleteAtISO?: string | null): string => {
  if (!deleteAtISO) return "";
  const deleteTime = new Date(deleteAtISO).getTime();
  const now = Date.now();
  const remainingMs = deleteTime - now;

  if (remainingMs <= 0) return "Deleting now...";

  const totalSeconds = Math.floor(remainingMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`);

  return `Deletes in ${parts.join(' ')}`;
};


export default function ManagedRulesPage() {
  const [hoveredRuleKey, setHoveredRuleKey] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<[string, RuleValue] | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionRuleKey, setActionRuleKey] = useState<string | null>(null);

  const [, setTick] = useState(0);
  useEffect(() => {
    const intervalId = setInterval(() => {
      setTick(prevTick => prevTick + 1);
    }, 1000);
    return () => clearInterval(intervalId);
  }, []);


  const { 
    data: overviewData, 
    error: fetchApiError,
    isLoading: isOverviewLoading,
    isValidating: isOverviewValidating,
    mutate
  } = useSWR<DockFlareFullOverview>(API_OVERVIEW_URL, fetcher, {
    revalidateOnFocus: true,
  });

  const rulesData = useMemo(() => overviewData?.rules || null, [overviewData]);
  const ruleArray = useMemo(() => (rulesData ? Object.entries(rulesData) : []), [rulesData]);

  const handleRetry = useCallback(() => {
    mutate();
  }, [mutate]);

  const handleMouseEnter = useCallback((ruleKey: string) => setHoveredRuleKey(ruleKey), []);
  const handleMouseLeave = useCallback(() => setHoveredRuleKey(null), []);

  const handleDeleteClick = useCallback((ruleKey: string, rule: RuleValue) => {
    setRuleToDelete([ruleKey, rule]);
    setShowDeleteConfirm(true);
  }, []);

  const confirmDeleteRule = useCallback(async () => {
    if (!ruleToDelete) return;
    
    const [ruleKeyToDelete, ruleValueToDelete] = ruleToDelete;
    setActionRuleKey(ruleKeyToDelete);
    setIsDeleting(true);

    mutate(
      (currentData) => {
        if (!currentData || !currentData.rules) return currentData;
        const updatedRules = { ...currentData.rules };
        delete updatedRules[ruleKeyToDelete];
        return { ...currentData, rules: updatedRules };
      }, 
      false 
    );

    try {
      if (ruleValueToDelete.source === 'manual') {
        await deleteManualRuleApi(ruleKeyToDelete);
      } else {
        console.warn("Attempted to delete a non-manual rule via simple delete:", ruleKeyToDelete);
        throw new Error("This delete function is for manual rules only.");
      }
    } catch (error) {
      console.error("Failed to delete rule:", error);
      mutate(); 
      alert(`Error deleting rule: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
      setRuleToDelete(null);
      setActionRuleKey(null);
    }
  }, [ruleToDelete, mutate]);

  const cancelDelete = useCallback(() => {
    setShowDeleteConfirm(false);
    setRuleToDelete(null);
  }, []);

  const handleForceDeleteClick = useCallback(async (ruleKey: string, rule: RuleValue) => {
    if (!confirm(`Are you sure you want to force delete the rule for ${rule.hostname_for_dns || ruleKey}? This will happen immediately and may affect running services if the source container is still up.`)) {
      return;
    }
    setActionRuleKey(ruleKey);
    setIsDeleting(true);

    mutate(
      (currentData) => {
        if (!currentData || !currentData.rules) return currentData;
        const updatedRules = { ...currentData.rules };
        delete updatedRules[ruleKey];
        return { ...currentData, rules: updatedRules };
      },
      false 
    );

    try {
      await forceDeleteRuleApi(ruleKey);
    } catch (error) {
      console.error("Failed to force delete rule:", error);
      mutate(); 
      alert(`Error force deleting rule: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsDeleting(false);
      setActionRuleKey(null);
    }
  }, [mutate]);


  if (isOverviewLoading && !overviewData) {
    return <Loader />;
  }

  if (fetchApiError && !overviewData) {
    return (
      <GlassCard className="mt-8 text-center !border-red-500/70 p-6">
        <h2 className="text-2xl font-semibold text-red-400 mb-2">Error Loading Rules</h2>
        <p className="text-slate-300 mb-4">
          {fetchApiError.message || 'An unknown error occurred.'}
        </p>
        <button onClick={handleRetry} className="mt-4 px-6 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-md font-semibold">
          Retry
        </button>
      </GlassCard>
    );
  }

  const portalSize = 64; 

  const getFullUrl = (hostname: string, path?: string | null): string => {
    const protocol = 'https://';
    const basePath = path && path !== '/' ? path : '';
    return `${protocol}${hostname}${basePath}`;
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
          Managed Ingress Rules
        </h1>
        {isOverviewValidating && overviewData && (
          <span className="text-xs text-slate-400 animate-pulse">Updating...</span>
        )}
        {fetchApiError && overviewData && (
             <span className="text-xs text-red-400" title={fetchApiError.message}>Failed to update. Displaying cached rules.</span>
        )}
      </div>

      <GlassCard className="p-0 shadow-2xl overflow-hidden">
        <div className="overflow-x-auto rounded-xl">
          <table className="min-w-full divide-y divide-slate-700 relative">
            <thead className="bg-slate-800/60 sticky top-0 z-10 backdrop-blur-md">
              <tr>
                <th scope="col" className="pl-4 pr-2 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider sm:pl-6">Status</th>
                <th scope="col" className="px-1 py-3.5 text-center w-10 h-full"><span className="sr-only">Left Portal Area</span></th> 
                <th scope="col" className="px-2 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Internal Service</th>
                <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Source</th>
                <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Hostname</th>
                <th scope="col" className="px-1 py-3.5 text-center w-10 h-full"><span className="sr-only">Right Portal Area</span></th>
                <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Path</th>
                <th scope="col" className="pl-2 pr-4 py-3.5 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider sm:pr-6">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-slate-900/40 divide-y divide-slate-700/50">
              {overviewData && ruleArray.length === 0 && !isOverviewLoading && !isOverviewValidating && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm text-slate-400 italic">
                    No managed ingress rules found.
                  </td>
                </tr>
              )}
              {isOverviewValidating && !rulesData && !isOverviewLoading && (
                 <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm text-slate-400 italic">
                    Checking for rules...
                  </td>
                </tr>
              )}
              {ruleArray.length > 0 && ruleArray.map(([ruleKey, rule]) => {
                  const isHovered = hoveredRuleKey === ruleKey;
                  const displayHostname = rule.hostname_for_dns || ruleKey.split('|')[0];
                  const isPendingDeletion = rule.status === 'pending_deletion';
                  const isButtonActionInProgress = isDeleting && actionRuleKey === ruleKey;

                  return (
                    <tr 
                      key={ruleKey} 
                      className={`relative hover:bg-slate-700/50 transition-colors duration-150 ease-in-out ${isHovered ? 'bg-slate-700/50' : ''}`}
                      onMouseEnter={() => handleMouseEnter(ruleKey)}
                      onMouseLeave={handleMouseLeave}
                    >
                      <td className="pl-4 pr-2 py-3 whitespace-nowrap text-sm sm:pl-6 align-middle">
                        <div className="flex flex-col items-start">
                          <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            rule.status === 'active' ? 'bg-green-500/30 text-green-200 border border-green-500/50' : 
                            isPendingDeletion ? 'bg-yellow-600/40 text-yellow-300 border border-yellow-600/60 animate-pulse' :
                            'bg-red-500/30 text-red-200 border border-red-500/50'
                          }`}>
                            {rule.status}
                          </span>
                          {isPendingDeletion && rule.delete_at && (
                            <span className="text-yellow-400 text-[10px] italic mt-0.5" title={`Actual deletion time: ${new Date(rule.delete_at).toLocaleString()}`}>
                              {formatRemainingTime(rule.delete_at)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="relative px-1 py-3 text-center w-10 align-middle">
                        <BluePortalEffect isVisible={isHovered} size={portalSize} />
                      </td>
                      <td className="px-2 py-3 whitespace-nowrap text-sm text-slate-300 font-mono break-all align-middle">{rule.service}</td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-400 align-middle">{rule.source}</td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-100 font-medium break-all align-middle">
                        {displayHostname ? (
                          <a 
                            href={`https://${displayHostname}`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="hover:text-cyan-300 hover:underline transition-colors"
                            title={`Open https://${displayHostname} in new tab`}
                          >
                            {displayHostname}
                          </a>
                        ) : (
                          <span className="italic text-slate-500">N/A</span>
                        )}
                      </td>
                      <td className="relative px-1 py-3 text-center w-10 align-middle">
                       <OrangePortalEffect isVisible={isHovered} size={portalSize} />
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-slate-300 align-middle">
                        {displayHostname ? (
                           <a
                            href={getFullUrl(displayHostname, rule.path)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-cyan-300 hover:underline transition-colors"
                            title={`Open ${getFullUrl(displayHostname, rule.path)} in new tab`}
                          >
                            {rule.path || <span className="italic text-slate-500">/ (root)</span>}
                          </a>
                        ) : (
                          rule.path || <span className="italic text-slate-500">/ (root)</span>
                        )}
                      </td>
                      <td className="pl-2 pr-4 py-3 whitespace-nowrap text-sm space-x-2 sm:pr-6 align-middle">
                        {isPendingDeletion ? (
                          <button 
                            onClick={() => handleForceDeleteClick(ruleKey, rule)}
                            disabled={isButtonActionInProgress}
                            className="text-orange-400 hover:text-orange-300 transition-colors text-xs font-medium relative z-[5] disabled:opacity-50"
                            title="Delete this rule from Cloudflare immediately"
                          >
                            {isButtonActionInProgress ? 'Forcing...' : 'Force Delete'}
                          </button>
                        ) : (
                          <button 
                            onClick={() => { alert('Edit Policy clicked for ' + ruleKey + '. Implement me!'); }}
                            className="text-cyan-400 hover:text-cyan-200 transition-colors text-xs font-medium relative z-[5]"
                          >
                            Edit Policy
                          </button>
                        )}

                        {rule.source === 'manual' && !isPendingDeletion && (
                          <button 
                            onClick={() => handleDeleteClick(ruleKey, rule)}
                            disabled={isButtonActionInProgress}
                            className="text-red-400 hover:text-red-200 transition-colors text-xs font-medium relative z-[5] disabled:opacity-50"
                          >
                            {isButtonActionInProgress && ruleToDelete?.[0] === ruleKey ? 'Deleting...' : 'Delete'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      </GlassCard>

      {showDeleteConfirm && ruleToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4">
          <GlassCard className="w-full max-w-md p-6 shadow-2xl border border-slate-700">
            <h3 className="text-xl font-semibold text-slate-100 mb-3">Confirm Deletion</h3>
            <p className="text-slate-300 mb-6">
              Are you sure you want to delete the rule for <strong className="font-mono text-cyan-300 break-all">{ruleToDelete[0]}</strong>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={cancelDelete}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-md transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteRule}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50"
              >
                {isDeleting && ruleToDelete?.[0] === ruleToDelete[0] ? 'Deleting...' : 'Delete Rule'}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}