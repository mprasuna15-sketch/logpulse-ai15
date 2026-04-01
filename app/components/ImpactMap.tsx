import React from 'react';
import { motion } from 'framer-motion';
import { Server, Database, Cloud, Shield, Activity } from 'lucide-react';

interface NodeProps {
    name: string;
    status: 'healthy' | 'warning' | 'error';
    icon: React.ElementType;
    x: number;
    y: number;
}

const Node = ({ name, status, icon: Icon, x, y }: NodeProps) => {
    const colors = {
        healthy: { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a' },
        warning: { bg: '#fffbeb', border: '#fef3c7', text: '#d97706' },
        error: { bg: '#fef2f2', border: '#fecaca', text: '#dc2626' },
    };

    const currentStyle = colors[status];

    return (
        <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                padding: 12,
                borderRadius: 12,
                border: `1px solid ${currentStyle.border}`,
                background: currentStyle.bg,
                color: currentStyle.text,
                zIndex: 10,
                width: 100,
                boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
            }}
        >
            <div style={{ padding: 6, borderRadius: 8, background: 'rgba(255,255,255,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={18} className={status === 'error' ? 'animate-pulse' : ''} />
            </div>
            <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{name}</span>
            {status !== 'healthy' && (
                <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }}
                />
            )}
        </motion.div>
    );
};

export const ImpactMap = ({ stats }: { stats: any }) => {
    const apiStatus = stats.errorRate > 5 ? 'error' : stats.errorRate > 1 ? 'warning' : 'healthy';
    const dbStatus = stats.avgLatency > 500 ? 'warning' : 'healthy';
    const securityStatus = stats.securityEvents > 0 ? 'error' : 'healthy';

    return (
        <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: 16, marginBottom: 16, position: 'relative', overflow: 'hidden', height: 260, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: '0 0 4px 8px' }}>System Health Topology</h3>
            <p style={{ fontSize: 10, color: '#94a3b8', margin: '0 0 20px 8px', fontStyle: 'italic' }}>Real-time service dependency monitoring</p>

            <div style={{ position: 'absolute', inset: 0, opacity: 0.03, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
                <Activity size={180} color="#6366f1" />
            </div>

            <div style={{ position: 'relative', height: '100%', width: '100%' }}>
                <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                    <line x1="20%" y1="50%" x2="45%" y2="50%" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4" />
                    <line x1="45%" y1="50%" x2="70%" y2="50%" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4" />
                    <line x1="45%" y1="50%" x2="45%" y2="20%" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4" />
                </svg>

                <Node name="Gateway" status="healthy" icon={Cloud} x={10} y={35} />
                <Node name="API Core" status={apiStatus} icon={Server} x={36} y={35} />
                <Node name="Database" status={dbStatus} icon={Database} x={65} y={35} />
                <Node name="Security" status={securityStatus} icon={Shield} x={36} y={5} />
            </div>
        </div>
    );
};
