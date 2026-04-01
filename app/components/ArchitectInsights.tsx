import React from 'react';
import { Insight } from '@/lib/types';
import { ShieldAlert, TrendingDown, AlertTriangle, Lightbulb, CheckCircle } from 'lucide-react';

interface Props {
    insights: Insight[];
}

export function ArchitectInsights({ insights }: Props) {
    if (insights.length === 0) {
        return (
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <div style={{ padding: 8, background: '#f0fdf4', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <CheckCircle size={18} color="#16a34a" />
                </div>
                <div>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: 0 }}>System Healthy</h3>
                    <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>No architectural or security risks detected.</p>
                </div>
            </div>
        );
    }

    const sorted = [...insights].sort((a, b) => {
        const score = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
        return score[b.severity] - score[a.severity];
    });

    const getSeverityStyles = (severity: string) => {
        switch (severity) {
            case 'CRITICAL': return { bg: '#fef2f2', border: '#fecaca', text: '#dc2626', iconBg: '#fee2e2' };
            case 'HIGH': return { bg: '#fffbeb', border: '#fef3c7', text: '#d97706', iconBg: '#fef3c7' };
            case 'MEDIUM': return { bg: '#eff6ff', border: '#dbeafe', text: '#2563eb', iconBg: '#dbeafe' };
            default: return { bg: '#f8fafc', border: '#e2e8f0', text: '#475569', iconBg: '#f1f5f9' };
        }
    };

    return (
        <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, marginBottom: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Lightbulb size={18} color="#eab308" />
                <div>
                    <h2 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', margin: 0 }}>Architectural Insights</h2>
                    <p style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>Automated Risk & Impact Analysis</p>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {sorted.map(insight => {
                    const styles = getSeverityStyles(insight.severity);
                    return (
                        <div
                            key={insight.id}
                            style={{
                                background: styles.bg,
                                border: `1px solid ${styles.border}`,
                                borderRadius: 8,
                                padding: 14,
                                position: 'relative'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                                <div style={{ display: 'flex', gap: 12 }}>
                                    <div style={{
                                        padding: 8,
                                        borderRadius: 6,
                                        background: styles.iconBg,
                                        color: styles.text,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        height: 'fit-content'
                                    }}>
                                        {insight.type === 'SECURITY' && <ShieldAlert size={16} />}
                                        {insight.type === 'BUSINESS' && <TrendingDown size={16} />}
                                        {insight.type === 'RELIABILITY' && <AlertTriangle size={16} />}
                                        {insight.type === 'PERFORMANCE' && <TrendingDown size={16} style={{ transform: 'rotate(180deg)' }} />}
                                    </div>

                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                                            <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'white', border: `1px solid ${styles.border}`, color: styles.text }}>
                                                {insight.severity}
                                            </span>
                                            <span style={{ fontSize: 9, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>{insight.type}</span>
                                        </div>
                                        <h4 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', margin: '0 0 4px 0' }}>{insight.title}</h4>
                                        <p style={{ fontSize: 12, color: '#475569', margin: '0 0 10px 0', lineHeight: 1.4 }}>
                                            {insight.description}
                                        </p>

                                        <div style={{ background: 'white', borderRadius: 6, padding: 10, fontSize: 11, borderLeft: '3px solid #2563eb' }}>
                                            <span style={{ fontWeight: 700, color: '#2563eb', marginRight: 6 }}>Recommendation:</span>
                                            <span style={{ color: '#475569' }}>{insight.recommendation}</span>
                                        </div>
                                    </div>
                                </div>

                                <div style={{ textAlign: 'right', display: 'none' }}>
                                    {/* Responsive hide handled via inline style would need more complex logic, but let's just keep it simple */}
                                </div>
                                <div style={{ textAlign: 'right', minWidth: 80 }}>
                                    <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{insight.affectedTraces}</div>
                                    <div style={{ fontSize: 9, color: '#94a3b8', textTransform: 'uppercase' }}>Affected Flows</div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
