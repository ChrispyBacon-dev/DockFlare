// src/components/features/logs/LogViewer.tsx
// line 91          {log.timestamp && <span className="text-slate-500 mr-2 select-none">{log.timestamp}</span>}
import React, { useEffect, useRef, useState } from 'react';
import { LogEntry } from '@/hooks/useRealtimeLogs';
import GlassCard from '@/components/ui/GlassCard';

interface LogViewerProps {
  logs: LogEntry[];
  title?: string;
  maxHeight?: string;
  isConnected?: boolean;
  className?: string;
}

const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  title = "Real-time Activity Logs",
  maxHeight = "300px", 
  isConnected,
  className = "",
}) => {
  const scrollableDivRef = useRef<HTMLDivElement>(null);
  const [isUserScrolledDown, setIsUserScrolledDown] = useState(false);

  useEffect(() => {
    if (scrollableDivRef.current && !isUserScrolledDown) {
      scrollableDivRef.current.scrollTop = 0;
    }
  }, [logs, isUserScrolledDown]); 

  useEffect(() => {
    const scrollableElement = scrollableDivRef.current;
    const handleScroll = () => {
      if (scrollableElement) {
        if (scrollableElement.scrollTop > 50) { 
          setIsUserScrolledDown(true);
        } else if (scrollableElement.scrollTop <= 10) { 
          setIsUserScrolledDown(false);
        }
      }
    };

    if (scrollableElement) {
      scrollableElement.addEventListener('scroll', handleScroll);
    }
    return () => {
      if (scrollableElement) {
        scrollableElement.removeEventListener('scroll', handleScroll);
      }
    };
  }, []); 

  const getLogColor = (level?: LogEntry['level']) => {
    switch (level?.toUpperCase()) {
      case 'ERROR': return 'text-red-400';
      case 'WARNING': return 'text-yellow-400';
      case 'INFO': return 'text-sky-300';
      case 'DEBUG': return 'text-purple-400';
      default: return 'text-slate-400';
    }
  };

  const hasDisplayableUserLogs = logs.some(log => !log.rawMessage.startsWith('--- Log stream'));

  return (
    <GlassCard className={`flex flex-col h-full ${className} relative`}> 
      <div className="flex justify-between items-center mb-3 px-1">
        <h2 className="text-xl font-semibold text-slate-200">{title}</h2>
        {isConnected !== undefined && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            isConnected ? 'bg-green-500/30 text-green-300' : 'bg-red-500/30 text-red-300 animate-pulse'
          }`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        )}
      </div>
      <div
        ref={scrollableDivRef}
        className="flex-grow bg-slate-800/70 p-3 rounded-md overflow-y-auto shadow-inner"
        style={{ maxHeight: maxHeight, minHeight: '150px' }}
      >
        {!hasDisplayableUserLogs && isConnected && logs.length <= 3 && ( 
             <p className="text-slate-500 italic text-center py-4">Log stream connected. Waiting for activity...</p>
        )}
        {!isConnected && logs.length <= 3 && (
             <p className="text-slate-500 italic text-center py-4">Attempting to connect to log stream...</p>
        )}

        {logs.map((log) => (
          <div key={log.id} className="text-xs mb-0.5 font-mono break-all" title={log.rawMessage}> 

            {log.level && !log.rawMessage.startsWith('---') && (
              <span className={`font-semibold mr-1 ${getLogColor(log.level)}`}>
                [{log.level}]
              </span>
            )}
            {log.source && !log.rawMessage.startsWith('---') && (
                <span className="text-cyan-400 mr-1">[{log.source}]</span>
            )}
            <span className={log.level && !log.rawMessage.startsWith('---') ? getLogColor(log.level) : 'text-slate-300'}>
                {log.message}
            </span>
          </div>
        ))}
      </div>
      {isUserScrolledDown && (
        <button
          onClick={() => {
            setIsUserScrolledDown(false); 
            if (scrollableDivRef.current) {
              scrollableDivRef.current.scrollTop = 0;
            }
          }}
          className="absolute bottom-4 right-4 sm:bottom-6 sm:right-6 z-10 bg-cyan-600/90 hover:bg-cyan-500 text-white text-xs font-semibold px-3 py-1.5 rounded-full shadow-lg backdrop-blur-sm transition-opacity duration-150 ease-in-out"
        >
          Show Latest
        </button>
      )}
    </GlassCard>
  );
};

export default LogViewer;