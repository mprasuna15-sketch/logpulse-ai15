'use client';

import React from 'react';
import { Bottleneck, EndpointHistory } from '@/lib/types';
import { Microscope, Zap, Database, Globe, Cpu, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface Props {
  bottlenecks: Bottleneck[];
  history: EndpointHistory[];
}

export function PerformanceLab({ bottlenecks, history }: Props) {
  if (bottlenecks.length === 0 && history.length === 0) return null;

  return (
    <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, marginBottom: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <Microscope size={18} color="#4f46e5" />
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', margin: 0 }}>Performance Lab</h2>
          <p style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
            Bottleneck Detection & Historical Trends
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
        {/* Bottlenecks Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
            <Zap size={14} /> Active Bottlenecks
          </h3>
          {bottlenecks.length === 0 ? (
            <div style={{ padding: 12, background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, color: '#166534', fontSize: 12 }}>
              No active bottlenecks detected. System is running optimally.
            </div>
          ) : (
            bottlenecks.map((b, i) => (
              <div key={i} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {b.type === 'DB' && <Database size={16} color="#2563eb" />}
                    {b.type === 'UPSTREAM' && <Globe size={16} color="#ea580c" />}
                    {b.type === 'CODE' && <Cpu size={16} color="#db2777" />}
                    <span style={{ fontWeight: 700, color: '#0f172a', fontSize: 13 }}>{b.type} Constrained</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#475569', background: 'white', border: '1px solid #e2e8f0', padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                    ~{b.latencyMs}ms avg
                  </span>
                </div>
                <p style={{ color: '#475569', fontSize: 12, lineHeight: 1.4, margin: '0 0 10px 0' }}>{b.description}</p>
                <div style={{ width: '100%', background: '#e2e8f0', height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 12 }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${b.confidence * 100}%`,
                      background: b.type === 'DB' ? '#3b82f6' : b.type === 'UPSTREAM' ? '#f97316' : '#ec4899'
                    }}
                  />
                </div>
                <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 6, padding: 10, fontSize: 11 }}>
                  <span style={{ fontWeight: 700, color: '#1e293b', display: 'block', marginBottom: 4 }}>Recommended Action:</span>
                  <span style={{ color: '#475569' }}>{b.recommendation}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#94a3b8', marginTop: 8, fontWeight: 600, textTransform: 'uppercase' }}>
                  <span>Confidence Score</span>
                  <span>{Math.round(b.confidence * 100)}%</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* History / Trends Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
            <ArrowUpRight size={14} /> Endpoint Regression History
          </h3>
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: 'white', borderBottom: '1px solid #e2e8f0' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Endpoint</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Trend</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right', fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Avg Latency</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: 24, textAlign: 'center', color: '#94a3b8', fontSize: 11 }}>
                      Not enough variance to determine trends.
                    </td>
                  </tr>
                ) : (
                  history.map((h, i) => (
                    <tr key={i} style={{ borderBottom: i === history.length - 1 ? 'none' : '1px solid #e2e8f0' }}>
                      <td style={{ padding: '10px 12px', color: '#475569', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={h.path}>
                        {h.path}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            fontWeight: 600,
                            color: h.trend === 'DEGRADING' ? '#dc2626' : h.trend === 'IMPROVING' ? '#16a34a' : '#64748b'
                          }}
                        >
                          {h.trend === 'DEGRADING' && <ArrowUpRight size={14} />}
                          {h.trend === 'IMPROVING' && <ArrowDownRight size={14} />}
                          {h.trend === 'STABLE' && <Minus size={14} />}
                          <span>{h.changePercent > 0 ? '+' : ''}{h.changePercent}%</span>
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{h.currAvgLatency}ms</span>
                        <span style={{ color: '#94a3b8', fontSize: 10, marginLeft: 6 }}>({h.prevAvgLatency}ms)</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div style={{ padding: 10, background: '#eef2ff', borderRadius: 8, border: '1px solid #c7d2fe', fontSize: 10, color: '#4338ca' }}>
            <span style={{ fontWeight: 700, marginRight: 4 }}>Pro Tip:</span> Endpoints degrading &gt;10% are auto-flagged for Code Review.
          </div>
        </div>
      </div>
    </div>
  );
}