import { useState, useEffect, useRef } from 'react';

export interface LogStreamStats {
    total: number;
    streaming: boolean;
}

export function useLogStream(url: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:9005') {
    const [isLiveStreaming, setIsLiveStreaming] = useState(false);
    const [liveStats, setLiveStats] = useState<LogStreamStats>({ total: 0, streaming: false });
    const [recentLogs, setRecentLogs] = useState<any[]>([]);
    const [alerts, setAlerts] = useState<any[]>([]);

    const wsRef = useRef<WebSocket | null>(null);
    const logBatchQueue = useRef<any[]>([]);
    const batchIntervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        connectWebSocket();

        // Batch processing interval (every 500ms)
        batchIntervalRef.current = setInterval(() => {
            if (logBatchQueue.current.length > 0) {
                const batch = [...logBatchQueue.current];
                logBatchQueue.current = [];

                setRecentLogs((prevLogs) => {
                    // Prepend the new batch and keep only the latest 1000 logs
                    return [...batch, ...prevLogs].slice(0, 1000);
                });
            }
        }, 500);

        return () => {
            wsRef.current?.close();
            if (batchIntervalRef.current) clearInterval(batchIntervalRef.current);
        };
    }, []);

    const connectWebSocket = () => {
        try {
            const ws = new WebSocket(`${url}/ws/logs`);

            ws.onopen = () => {
                console.log('WebSocket connected - Live streaming active');
                setIsLiveStreaming(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'initial_load') {
                        console.log('Initial logs loaded:', data.total_logs);
                        setLiveStats(prev => ({ ...prev, total: data.total_logs }));
                        // We could seed initial logs here if we wanted, 
                        // but typically we fetch full state via REST API on load.
                    } else if (data.type === 'new_log') {
                        logBatchQueue.current.push(data.log); // Keep arrival order (Newest -> Oldest)
                        setLiveStats(prev => ({
                            ...prev,
                            total: data.total_logs
                        }));
                    } else if (data.type === 'alert') {
                        setAlerts(prev => [data, ...prev].slice(0, 10));
                    }
                } catch (e) {
                    console.error("Error parsing WS message", e);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setIsLiveStreaming(false);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                setIsLiveStreaming(false);
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    connectWebSocket();
                }, 5000);
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            setIsLiveStreaming(false);
        }
    };

    return { isLiveStreaming, liveStats, recentLogs, setRecentLogs, alerts, setAlerts };
}
