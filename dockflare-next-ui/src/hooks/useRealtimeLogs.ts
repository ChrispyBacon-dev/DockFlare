// src/hooks/useRealtimeLogs.ts
import { useState, useEffect, useRef, useCallback } from 'react';

export interface UseRealtimeLogsOptions {
  streamUrl: string;
  maxLines?: number;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
  autoConnect?: boolean;
}

export interface LogEntry {
  id: string; 
  rawMessage: string; 
  timestamp?: string; 
  level?: 'INFO' | 'ERROR' | 'WARNING' | 'DEBUG' | string; 
  source?: string; 
  message: string; 
}

const LOG_LINE_REGEX = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(INFO|ERROR|WARNING|DEBUG)\]\s+\[([^\]]+)\]\s+(.*)$/i;

// Default max lines constant -> jo nicht vergessen.... we need to tweak here... but yea later when we do filters
const MAX_LOG_LINES_DEFAULT = 200;

export function useRealtimeLogs({
  streamUrl,
  maxLines = MAX_LOG_LINES_DEFAULT,
  initialReconnectDelay = 1000,
  maxReconnectDelay = 30000,
  autoConnect = true,
}: UseRealtimeLogsOptions) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [errorCount, setErrorCount] = useState(0);
  const [messageCount, setMessageCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectDelayRef = useRef(initialReconnectDelay);
  const connectTimeoutIdRef = useRef<NodeJS.Timeout | null>(null);

  console.log(`[useRealtimeLogs] Hook instance created/re-rendered. streamUrl: ${streamUrl}, autoConnect: ${autoConnect}, maxLines: ${maxLines}`);

  const appendLog = useCallback((logEntry: LogEntry) => {
    setLogs(prevLogs => {
      const newLogsArray = [logEntry, ...prevLogs].slice(0, maxLines);
      return newLogsArray;
    });
  }, [maxLines]);

  const disconnect = useCallback(() => {
    console.log("[useRealtimeLogs] disconnect() called.");
    if (connectTimeoutIdRef.current) {
      clearTimeout(connectTimeoutIdRef.current);
      connectTimeoutIdRef.current = null;
      console.log("[useRealtimeLogs] Cleared connect timeout.");
    }
    if (eventSourceRef.current) {
      console.log(`[useRealtimeLogs] Closing EventSource. Current readyState: ${eventSourceRef.current.readyState}`);
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(prev => {
        if (prev) {
            console.log("[useRealtimeLogs] Setting isConnected to false in disconnect.");
            return false;
        }
        return prev;
    });
  }, []);

  const connect = useCallback(() => {
    console.log(`[useRealtimeLogs] connect() called for URL: ${streamUrl}`);
    disconnect();

    if (!streamUrl) {
      console.warn("[useRealtimeLogs] streamUrl is not provided. Cannot connect.");
      return;
    }

    console.log(`[useRealtimeLogs] Creating new EventSource for ${streamUrl}`);
    const es = new EventSource(streamUrl, { withCredentials: false });
    eventSourceRef.current = es;
    reconnectDelayRef.current = initialReconnectDelay;
    setMessageCount(0);

    es.onopen = () => {
      console.log(`[useRealtimeLogs] EventSource OPENED for ${streamUrl}.`);
      setIsConnected(true);
      appendLog({
          id: Date.now().toString() + Math.random().toString(36).substring(7) + '_conn',
          rawMessage: '--- Log stream connected ---',
          message: '--- Log stream connected ---',
          level: 'INFO'
      });
      reconnectDelayRef.current = initialReconnectDelay;
    };

    es.onmessage = (event) => {
      setMessageCount(prev => prev + 1);
      const rawMsg: string = event.data;
      
      let parsedLogParts: Partial<Omit<LogEntry, 'id' | 'rawMessage'>> = { message: rawMsg, level: 'INFO' };
      const match = rawMsg.match(LOG_LINE_REGEX);

      if (match) {
        parsedLogParts = {
          timestamp: match[1],
          level: match[2].toUpperCase() as LogEntry['level'],
          source: match[3],
          message: match[4].trim(),
        };
      } else if (rawMsg.startsWith('---')) {
        parsedLogParts.level = rawMsg.toLowerCase().includes('error') || rawMsg.toLowerCase().includes('disconnected') ? 'ERROR' : 'INFO';
      }
      
      appendLog({
        id: Date.now().toString() + Math.random().toString(36).substring(7),
        rawMessage: rawMsg,
        message: parsedLogParts.message || rawMsg,
        level: parsedLogParts.level,
        timestamp: parsedLogParts.timestamp,
        source: parsedLogParts.source,
      });
    };

    es.onerror = (errorEvent) => {
      setErrorCount(prev => prev + 1);
      console.error(`[useRealtimeLogs] EventSource ERROR (count: ${errorCount + 1}). ReadyState: ${es.readyState}`, errorEvent);
      
      setIsConnected(prev => {
        if (prev) {
            console.log("[useRealtimeLogs] Setting isConnected to false in onerror.");
            return false;
        }
        return prev;
      });

      if (es.readyState === EventSource.CLOSED) {
        console.log("[useRealtimeLogs] EventSource is CLOSED. Attempting reconnect.");
        eventSourceRef.current = null;
        appendLog({
            id: Date.now().toString() + Math.random().toString(36).substring(7) + '_err_closed',
            rawMessage: `--- Log stream disconnected. Reconnecting in ${reconnectDelayRef.current / 1000}s... ---`,
            message: `--- Log stream disconnected. Reconnecting in ${reconnectDelayRef.current / 1000}s... ---`,
            level: 'ERROR'
        });

        if (connectTimeoutIdRef.current) clearTimeout(connectTimeoutIdRef.current);
        connectTimeoutIdRef.current = setTimeout(() => {
          if (autoConnect && eventSourceRef.current === null) {
            console.log("[useRealtimeLogs] Reconnect timeout triggered. Calling connect().");
            connect();
          } else {
            console.log("[useRealtimeLogs] Reconnect timeout triggered, but conditions not met for reconnect (autoConnect off or already reconnected).");
          }
        }, reconnectDelayRef.current);
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 1.5, maxReconnectDelay);
      } else {
        console.warn("[useRealtimeLogs] EventSource error, but not CLOSED. EventSource might attempt its own recovery. ReadyState:", es.readyState);
      }
    };
  }, [
    streamUrl,
    appendLog,
    disconnect,
    initialReconnectDelay,
    maxReconnectDelay,
    autoConnect,
  ]);

  useEffect(() => {
    console.log(`[useRealtimeLogs] Main effect triggered. autoConnect: ${autoConnect}, streamUrl: ${streamUrl}`);
    if (autoConnect && streamUrl) {
      console.log("[useRealtimeLogs] Main effect: Calling connect()");
      connect();
    } else {
      console.log("[useRealtimeLogs] Main effect: autoConnect is false or no streamUrl. Calling disconnect().");
      disconnect();
    }
    
    return () => {
      console.log("[useRealtimeLogs] Main effect CLEANUP. Calling disconnect().");
      disconnect();
    };
  }, [streamUrl, autoConnect, connect, disconnect]);

  return { logs, isConnected, connect, disconnect, messageCount, errorCount };
}