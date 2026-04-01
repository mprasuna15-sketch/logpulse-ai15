'use client';

import { DailyStats } from '@/lib/types';
import { AlertCircle, Clock, CheckCircle, ShieldAlert } from 'lucide-react';

export function IssuesList({ stats }: { stats: DailyStats }) {
    const issues = [];

    if (stats.errorRate > 1) {
        issues.push({
            id: 'err-rate',
            title: 'High Error Rate',
            severity: 'high',
            type: 'HEALTH',
            desc: `Error rate is ${stats.errorRate.toFixed(2)}%, which is above the 1% threshold.`,
            icon: AlertCircle
        });
    }

    if (stats.securityEvents > 0) {
        issues.push({
            id: 'sec-events',
            title: 'Security Threats Detected',
            severity: 'high',
            type: 'SECURITY',
            desc: `Detected ${stats.securityEvents} security-related logs including potential hack attempts.`,
            icon: ShieldAlert
        });
    }

    stats.topEndpoints.forEach(ep => {
        if (ep.avgLatency > 500) {
            issues.push({
                id: `slow-${ep.path}`,
                title: `Slow Endpoint: ${ep.path}`,
                severity: 'medium',
                type: 'PERFORMANCE',
                desc: `Avg latency: ${ep.avgLatency}ms. Needs optimization.`,
                icon: Clock
            });
        }
    });

    return (
        <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.03)', height: '100%' }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: '0 0 12px 0' }}>Insights & Recommendations</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {issues.length === 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0', color: '#166534', fontSize: 12 }}>
                        <CheckCircle size={16} />
                        <span>No major issues detected. Great job!</span>
                    </div>
                ) : (
                    issues.map(issue => (
                        <div key={issue.id} style={{ display: 'flex', gap: 12, padding: 12, borderRadius: 8, background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                            <div style={{
                                padding: 8,
                                borderRadius: 6,
                                background: issue.type === 'SECURITY' ? '#fef2f2' : (issue.severity === 'high' ? '#fffbeb' : '#eff6ff'),
                                color: issue.type === 'SECURITY' ? '#dc2626' : (issue.severity === 'high' ? '#d97706' : '#2563eb'),
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <issue.icon size={16} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <h4 style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', margin: 0 }}>{issue.title}</h4>
                                <p style={{ fontSize: 11, color: '#64748b', marginTop: 4, margin: 0 }}>{issue.desc}</p>
                                <button style={{ marginTop: 8, fontSize: 11, fontWeight: 600, color: '#2563eb', background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                                    Suggest Fix →
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
