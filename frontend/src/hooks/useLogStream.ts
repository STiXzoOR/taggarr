import { useEffect, useState, useCallback } from "react";

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  module: string;
  funcName: string;
  lineno: number;
}

const MAX_LOG_ENTRIES = 500;

export function useLogStream() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/logs`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const logEntry: LogEntry = JSON.parse(event.data);
        setLogs((prev) => [...prev, logEntry].slice(-MAX_LOG_ENTRIES));
      } catch {
        console.error("Failed to parse log entry:", event.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setError("WebSocket connection failed");
      setIsConnected(false);
    };

    return ws;
  }, []);

  useEffect(() => {
    const ws = connect();

    return () => {
      ws.close();
    };
  }, [connect]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return {
    logs,
    isConnected,
    error,
    clearLogs,
  };
}
