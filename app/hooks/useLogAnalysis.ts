import { useState, useCallback } from 'react';
import { parseLogs } from '@/lib/logParser';
import { analyzeLogs } from '@/lib/analysis';
import { getApiConfig } from '@/lib/config';

export type TimeFilter = '1h' | '2h' | '5h' | '24h' | '7d' | '30d';

export function useLogAnalysis(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9005') {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [timePeriod, setTimePeriod] = useState('');
    const [error, setError] = useState<string | null>(null);

    const fetchLogs = useCallback(async (timeFilter: TimeFilter, customStart?: number, customEnd?: number) => {
        setLoading(true);
        setError(null);
        try {
            const { apiKey } = getApiConfig();
            const body: any = { time_filter: timeFilter };
            if (customStart && customEnd) {
                body.custom_start = customStart;
                body.custom_end = customEnd;
            }

            const res = await fetch(`${baseUrl}/logs/filter`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify(body)
            });

            if (!res.ok) throw new Error(`API Error: ${res.statusText}`);

            const data = await res.json();

            const parsed = parseLogs(data.logs || []);

            const timeToHours: Record<string, number> = {
                '1h': 1, '2h': 2, '5h': 5, '24h': 24, '7d': 168, '30d': 720
            };

            const analyzed = analyzeLogs(parsed, timeToHours[timeFilter] || 24);
            setResult(analyzed);
            setTimePeriod(data.time_period);

            return analyzed;
        } catch (err: any) {
            console.error('Failed to fetch logs:', err);
            setError(err.message || 'Failed to fetch logs');
            setResult({ error: err.message }); // Fallback to allow UI to show error state
        } finally {
            setLoading(false);
        }
    }, [baseUrl]);

    const refreshLogs = useCallback(async (timeFilter: TimeFilter) => {
        setLoading(true);
        try {
            const { apiKey } = getApiConfig();
            await fetch(`${baseUrl}/logs/refresh`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({ time_filter: timeFilter })
            });
            await fetchLogs(timeFilter);
        } catch (err: any) {
            console.error("Refresh failed", err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [baseUrl, fetchLogs]);

    const getAlertHistory = useCallback(async (timeFilter: TimeFilter) => {
        setLoading(true);
        try {
            const { apiKey } = getApiConfig();
            const res = await fetch(`${baseUrl}/alerts/history?time_filter=${timeFilter}`, {
                method: 'GET',
                headers: { 
                    'Accept': 'application/json',
                    'X-API-Key': apiKey
                }
            });
            if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
            const data = await res.json();
            return data.alerts || [];
        } catch (err: any) {
            console.error("Failed to fetch alert history", err);
            return [];
        } finally {
            setLoading(false);
        }
    }, [baseUrl]);

    return {
        loading,
        result,
        timePeriod,
        fetchLogs,
        refreshLogs,
        getAlertHistory,
        error
    };
}
