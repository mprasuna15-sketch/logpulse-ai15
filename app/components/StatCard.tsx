import { LucideIcon } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: string | number;
    icon: LucideIcon;
    trend?: string;
    trendUp?: boolean;
    description?: string;
}

export function StatCard({ title, value, icon: Icon, trend, trendUp, description }: StatCardProps) {
    return (
        <div style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 10,
            padding: '14px 16px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            display: 'flex',
            flexDirection: 'column',
            gap: 4
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            {title}
                        </span>
                        {description && (
                            <div title={description} style={{ display: 'flex', alignItems: 'center', cursor: 'help' }}>
                                <Icon size={12} color="#94a3b8" />
                            </div>
                        )}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>
                        {value}
                    </div>
                </div>
                <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: '#eff6ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <Icon size={18} color="#2563eb" />
                </div>
            </div>
            {trend && (
                <div style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: trendUp ? '#16a34a' : '#dc2626',
                    marginTop: 2
                }}>
                    {trend}
                </div>
            )}
        </div>
    );
}
