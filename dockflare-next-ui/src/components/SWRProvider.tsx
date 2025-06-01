// src/components/SWRProvider.tsx
'use client';

import { SWRConfig } from 'swr';
import { fetcher } from '@/lib/fetchers'; // Your generic fetcher

export const SWRProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <SWRConfig 
      value={{
        fetcher: fetcher, // Default fetcher for all useSWR hooks
        // You can add other global options here, e.g.:
        // revalidateOnFocus: true,
        // dedupingInterval: 2000, // Dedupe requests for the same key within 2s
      }}
    >
      {children}
    </SWRConfig>
  );
};