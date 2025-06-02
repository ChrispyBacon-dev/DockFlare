// src/components/features/rules/AddManualRuleModal.tsx
'use client';

import React, { useState, useCallback } from 'react';
import { useSWRConfig } from 'swr';
import GlassCard from '@/components/ui/GlassCard';
import { ManualRulePayload, AccessPolicyType, ServiceType } from '@/lib/types';
import { addManualRuleApi } from '@/lib/api';

const API_OVERVIEW_URL = "/api/v2/overview";

interface AddManualRuleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const initialFormData: ManualRulePayload = {
  subdomain: '',
  domain_name: '',
  path: '',
  service_type: '' as ServiceType,
  service_address: '',
  no_tls_verify: false,
  origin_server_name: '',
  zone_name_override: '',
  access_policy_type: 'none',
  auth_email: '',
  access_session_duration: '24h',
  access_app_launcher_visible: true,
  access_auto_redirect: true,
};

const serviceTypes: { value: ServiceType; label: string; requiresAddress: boolean; prefix?: string; helpText?: string }[] = [
  { value: 'http', label: 'HTTP', requiresAddress: true, prefix: 'http://', helpText: 'e.g., 192.168.1.10:8000 or my-service.local' },
  { value: 'https', label: 'HTTPS', requiresAddress: true, prefix: 'https://', helpText: 'e.g., 192.168.1.10:443 or my-secure-service.local' },
  { value: 'tcp', label: 'TCP', requiresAddress: true, helpText: 'e.g., 192.168.1.10:2222 or hostname:port' },
  { value: 'ssh', label: 'SSH', requiresAddress: true, helpText: 'e.g., 192.168.1.10:22 or ssh-server:22' },
  { value: 'rdp', label: 'RDP', requiresAddress: true, helpText: 'e.g., 192.168.1.10:3389 or rdp-server:3389' },
  { value: 'http_status', label: 'HTTP Status Code', requiresAddress: true, helpText: 'e.g., 200 or 404 (blocks requests)' },
];

const accessPolicyTypes: { value: AccessPolicyType; label: string }[] = [
  { value: 'none', label: 'None (Public - No App)' },
  { value: 'bypass', label: 'Bypass (Public App)' },
  { value: 'authenticate_email', label: 'Authenticate by Email' },
  { value: 'default_tld', label: 'Use Default Account TLD Policy' },
];

export default function AddManualRuleModal({ isOpen, onClose }: AddManualRuleModalProps) {
  const [formData, setFormData] = useState<ManualRulePayload>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { mutate } = useSWRConfig();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
        const { checked } = e.target as HTMLInputElement;
        setFormData(prev => ({ ...prev, [name]: checked }));
    } else if (name === "path") {
        const pathValue = value.startsWith('/') ? value : `/${value}`;
        const finalPath = value.trim() === '' || value.trim() === '/' ? '' : pathValue;
        setFormData(prev => ({ ...prev, [name]: finalPath }));
    }
     else {
        setFormData(prev => ({ ...prev, [name]: value }));
    }
  };
  
  const handleServiceTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newServiceType = e.target.value as ServiceType;
    setFormData(prev => ({
      ...prev,
      service_type: newServiceType,
      service_address: serviceTypes.find(st => st.value === newServiceType)?.value === 'http_status' ? '' : prev.service_address,
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await addManualRuleApi(formData);
      mutate(API_OVERVIEW_URL);
      onClose();
      setFormData(initialFormData); // Reset form
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedServiceTypeDetails = serviceTypes.find(st => st.value === formData.service_type);
  const showAuthEmailField = formData.access_policy_type === 'authenticate_email';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4">
      <GlassCard className="w-full max-w-3xl p-0 shadow-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 bg-slate-800/50">
          <h3 className="text-xl font-semibold text-slate-100">Add New Manual Ingress Rule</h3>
        </div>
        
        <form onSubmit={handleSubmit} className="max-h-[calc(100vh-12rem)] overflow-y-auto">
          <div className="p-6 space-y-6">
            {error && (
              <div role="alert" className="alert alert-error text-sm p-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-5 w-5" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{error}</span>
              </div>
            )}

            <div>
              <h4 className="text-md font-semibold text-slate-200 mb-3">Public Hostname</h4>
              <div className="grid grid-cols-1 md:grid-cols-7 gap-4 items-start">
                <div className="form-control md:col-span-2">
                  <label htmlFor="subdomain" className="label pb-1"><span className="label-text text-slate-300 text-xs">Subdomain</span></label>
                  <input type="text" id="subdomain" name="subdomain" placeholder="(optional)" value={formData.subdomain || ''} onChange={handleChange} className="input input-sm input-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" />
                </div>
                <div className="form-control md:col-span-3">
                  <label htmlFor="domain_name" className="label pb-1"><span className="label-text text-slate-300 text-xs">Domain <span className="text-red-400">*</span></span></label>
                  <input type="text" id="domain_name" name="domain_name" placeholder="example.com" value={formData.domain_name} onChange={handleChange} required className="input input-sm input-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" />
                </div>
                <div className="form-control md:col-span-2">
                  <label htmlFor="path" className="label pb-1"><span className="label-text text-slate-300 text-xs">Path</span></label>
                  <div className="join w-full">
                      <span className="join-item btn btn-sm btn-disabled normal-case pointer-events-none !bg-slate-600/70 !border-slate-500 text-slate-300 px-3">/</span>
                      <input type="text" id="path" name="path" placeholder="app/path" value={(formData.path || '').replace(/^\//, '')} onChange={handleChange} className="input input-sm input-bordered join-item w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" />
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-md font-semibold text-slate-200 mb-3">Internal Service Target</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
                <div className="form-control">
                  <label htmlFor="service_type" className="label pb-1"><span className="label-text text-slate-300 text-xs">Type <span className="text-red-400">*</span></span></label>
                  <select id="service_type" name="service_type" value={formData.service_type} onChange={handleServiceTypeChange} required className="select select-sm select-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500">
                    <option value="" disabled>Select type...</option>
                    {serviceTypes.map(st => <option key={st.value} value={st.value}>{st.label}</option>)}
                  </select>
                </div>
                <div className="form-control">
                  <label htmlFor="service_address" className="label pb-1">
                    <span className="label-text text-slate-300 text-xs">
                      {selectedServiceTypeDetails?.value === 'http_status' ? 'Status Code' : 'Address / Host:Port'} <span className="text-red-400">*</span>
                    </span>
                  </label>
                  <div className="join w-full">
                    {selectedServiceTypeDetails?.prefix && <span className="join-item btn btn-sm btn-disabled normal-case pointer-events-none !bg-slate-600/70 !border-slate-500 text-slate-300 px-3">{selectedServiceTypeDetails.prefix}</span>}
                    <input 
                      type="text" 
                      id="service_address" 
                      name="service_address" 
                      placeholder={selectedServiceTypeDetails?.helpText || "e.g., host:port or status code"} 
                      value={formData.service_address} 
                      onChange={handleChange} 
                      required 
                      className="input input-sm input-bordered join-item w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" 
                    />
                  </div>
                   {selectedServiceTypeDetails?.helpText && <div className="text-xs text-slate-400 mt-1 px-1">{selectedServiceTypeDetails.helpText}</div>}
                </div>
              </div>
            </div>

            <div>
                <h4 className="text-md font-semibold text-slate-200 mb-3">Access Policy (Optional)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
                    <div className="form-control">
                        <label htmlFor="access_policy_type" className="label pb-1"><span className="label-text text-slate-300 text-xs">Policy Type</span></label>
                        <select 
                            id="access_policy_type" 
                            name="access_policy_type" 
                            value={formData.access_policy_type || 'none'} 
                            onChange={handleChange} 
                            className="select select-sm select-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500"
                        >
                            {accessPolicyTypes.map(ap => <option key={ap.value} value={ap.value || 'none'}>{ap.label}</option>)}
                        </select>
                    </div>
                    {showAuthEmailField && (
                        <div className="form-control">
                            <label htmlFor="auth_email" className="label pb-1"><span className="label-text text-slate-300 text-xs">Allowed Email(s) or Domain(s)</span></label>
                            <input 
                                type="text" 
                                id="auth_email" 
                                name="auth_email" 
                                placeholder="user@example.com, @domain.com" 
                                value={formData.auth_email || ''} 
                                onChange={handleChange} 
                                className="input input-sm input-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" 
                            />
                            <div className="text-xs text-slate-400 mt-1 px-1">Comma-separated.</div>
                        </div>
                    )}
                </div>
            </div>
            
            <div className="pt-4 border-t border-slate-700 space-y-4">
                <h4 className="text-md font-semibold text-slate-200 mb-1">Advanced Options</h4>
                <div className="form-control">
                    <label htmlFor="zone_name_override" className="label pb-1"><span className="label-text text-slate-300 text-xs">Cloudflare Zone Name (Override)</span></label>
                    <input 
                        type="text" 
                        id="zone_name_override" 
                        name="zone_name_override" 
                        placeholder="your-other-domain.com (if needed)" 
                        value={formData.zone_name_override || ''} 
                        onChange={handleChange} 
                        className="input input-sm input-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" 
                    />
                    <div className="text-xs text-slate-400 mt-1 px-1">If blank, DockFlare uses "Domain" or default CF_ZONE_ID.</div>
                </div>
                
                <div className="form-control">
                  <label className="label cursor-pointer justify-start gap-2 p-0">
                    <input 
                        type="checkbox" 
                        name="no_tls_verify" 
                        id="no_tls_verify" 
                        checked={!!formData.no_tls_verify}
                        onChange={handleChange}
                        className="checkbox checkbox-xs checkbox-info [--chkfg:theme(colors.sky.200)]" 
                    />
                    <span className="label-text text-slate-300 text-sm">Disable TLS Verification (No TLS Verify)</span>
                  </label>
                  <div className="text-xs text-slate-400 mt-0.5 ml-6">For origin services with self-signed SSL or HTTP. (HTTP/S only).</div>
                </div>

                <div className="form-control">
                    <label htmlFor="origin_server_name" className="label pb-1"><span className="label-text text-slate-300 text-xs">Origin Server Name (SNI)</span></label>
                    <input 
                        type="text" 
                        id="origin_server_name" 
                        name="origin_server_name" 
                        placeholder="internal.service.local (optional)" 
                        value={formData.origin_server_name || ''} 
                        onChange={handleChange} 
                        className="input input-sm input-bordered w-full bg-slate-700/50 border-slate-600 focus:border-cyan-500" 
                    />
                     <div className="text-xs text-slate-400 mt-1 px-1">Hostname for TLS SNI to origin. (HTTP/S only).</div>
                </div>
            </div>
          </div>

          <div className="p-4 bg-slate-800/50 border-t border-slate-700 flex justify-end space-x-3 sticky bottom-0">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="btn btn-sm btn-ghost text-slate-300 hover:bg-slate-700 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-sm btn-primary bg-cyan-600 hover:bg-cyan-700 border-cyan-500 hover:border-cyan-600 text-white disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <span className="loading loading-spinner loading-xs"></span>
                  Adding...
                </>
              ) : 'Add Rule'}
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}