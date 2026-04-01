'use client';

import React from 'react';
import { Layers, Shield, Zap, DollarSign, ArrowRight } from 'lucide-react';
import { StrategicInsight } from '@/lib/types';

interface Props {
  insights: StrategicInsight[];
}

export function StrategyPanel({ insights }: Props) {
  if (!insights || insights.length === 0) return null;

  return (
    <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, marginTop: 16, marginBottom: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ padding: 8, background: '#eff6ff', borderRadius: 8, border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Layers size={18} color="#2563eb" />
        </div>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', margin: 0 }}>Strategic Architecture Recommendations</h2>
          <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>High-level improvements derived from current bottlenecks</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12 }}>
        {insights.map((insight, i) => (
          <div
            key={i}
            style={{
              position: 'relative',
              overflow: 'hidden',
              borderRadius: 10,
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              padding: 14,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}
          >
            <div style={{ position: 'absolute', top: 0, right: 0, padding: 12, opacity: 0.05 }}>
              {insight.type === 'ARCHITECTURE' && <Layers size={48} />}
              {insight.type === 'RESILIENCE' && <Shield size={48} />}
              {insight.type === 'SCALING' && <Zap size={48} />}
              {insight.type === 'COST' && <DollarSign size={48} />}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8, position: 'relative', zIndex: 1 }}>
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 9,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  background: insight.type === 'ARCHITECTURE' ? '#e0e7ff' :
                    insight.type === 'RESILIENCE' ? '#ccfbf1' :
                      insight.type === 'SCALING' ? '#fef3c7' : '#fee2e2',
                  color: insight.type === 'ARCHITECTURE' ? '#4338ca' :
                    insight.type === 'RESILIENCE' ? '#0f766e' :
                      insight.type === 'SCALING' ? '#b45309' : '#b91c1c'
                }}
              >
                {insight.type}
              </span>
              <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 600 }}>
                Impact: <span style={{ color: '#475569' }}>{insight.impactLevel}</span>
              </span>
            </div>

            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 4, position: 'relative', zIndex: 1 }}>{insight.title}</h3>
            <p style={{ fontSize: 12, color: '#64748b', marginBottom: 12, lineHeight: 1.4, position: 'relative', zIndex: 1 }}>{insight.description}</p>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: 'white', padding: 8, borderRadius: 6, border: '1px solid #e2e8f0', position: 'relative', zIndex: 1 }}>
              <ArrowRight size={14} color="#2563eb" style={{ marginTop: 2, flexShrink: 0 }} />
              <p style={{ fontSize: 11, color: '#1e40af', fontWeight: 600, margin: 0 }}>{insight.action}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
