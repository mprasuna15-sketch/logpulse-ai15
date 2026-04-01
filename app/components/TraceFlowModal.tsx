'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Clock, AlertCircle, Database, Globe, Cpu } from 'lucide-react';
import { getApiConfig } from '@/lib/config';

interface TraceStep {
  id: string;
  timestamp: string;
  message: string;
  level: string;
  duration_ms: number | null;
  is_error: boolean;
  category: string;
  step_number: number;
}

interface TraceFlowData {
  correlation_id: string;
  steps: TraceStep[];
  total_duration_ms: number;
  start_time: string;
  end_time: string;
  status: string;
  error_steps: number[];
}

interface Props {
  correlationId: string;
  onClose: () => void;
}

export function TraceFlowModal({ correlationId, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [traceData, setTraceData] = useState<TraceFlowData | null>(null);

  const fetchTraceFlow = useCallback(async () => {
    setLoading(true);
    try {
      const { apiBaseUrl, apiKey } = getApiConfig();
      const res = await fetch(`${apiBaseUrl}/trace/flow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ correlation_id: correlationId })
      });

      const data = await res.json();
      setTraceData(data);
    } catch (error) {
      console.error('Failed to fetch trace flow:', error);
    } finally {
      setLoading(false);
    }
  }, [correlationId]);

  useEffect(() => {
    fetchTraceFlow();
  }, [fetchTraceFlow]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'DB':
        return <Database size={14} color="#2563eb" />;
      case 'EXTERNAL':
        return <Globe size={14} color="#ea580c" />;
      case 'HTTP':
        return <Cpu size={14} color="#16a34a" />;
      default:
        return <Clock size={14} color="#64748b" />;
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(255, 255, 255, 0.7)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, maxWidth: 800, width: '100%', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)' }}>
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', margin: 0 }}>Request Trace Flow</h2>
              {traceData && (
                <span style={{
                  padding: '2px 10px',
                  borderRadius: 999,
                  fontSize: 10,
                  fontWeight: 600,
                  background: traceData.status === 'SUCCESS' ? '#f0fdf4' : '#fef2f2',
                  color: traceData.status === 'SUCCESS' ? '#16a34a' : '#dc2626',
                  border: `1px solid ${traceData.status === 'SUCCESS' ? '#bbf7d0' : '#fecaca'}`
                }}>
                  {traceData.status}
                </span>
              )}
            </div>
            <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, fontFamily: 'monospace' }}>
              Correlation ID: {correlationId}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ padding: 8, background: 'none', border: 'none', cursor: 'pointer', borderRadius: 8, transition: 'background 0.2s', color: '#94a3b8' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f5f9')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 64 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#94a3b8' }}>
                <div style={{ width: 32, height: 32, border: '3px solid #f1f5f9', borderTopColor: '#4f46e5', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                <span>Loading trace flow...</span>
              </div>
            </div>
          ) : !traceData || traceData.steps.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 64, textAlign: 'center' }}>
              <AlertCircle size={48} color="#cbd5e1" style={{ marginBottom: 16 }} />
              <p style={{ color: '#64748b' }}>No trace data found for this correlation ID</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {/* Summary */}
              <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
                  <div>
                    <p style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, marginBottom: 4 }}>Start Time</p>
                    <p style={{ color: '#1e293b', fontFamily: 'monospace', fontSize: 13, margin: 0 }}>
                      {new Date(traceData.start_time).toLocaleTimeString()}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, marginBottom: 4 }}>End Time</p>
                    <p style={{ color: '#1e293b', fontFamily: 'monospace', fontSize: 13, margin: 0 }}>
                      {new Date(traceData.end_time).toLocaleTimeString()}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, marginBottom: 4 }}>Total Duration</p>
                    <p style={{ color: '#0f172a', fontWeight: 800, fontSize: 18, margin: 0 }}>
                      {traceData.total_duration_ms}ms
                    </p>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <h3 style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 16 }}>
                  Execution Timeline ({traceData.steps.length} steps)
                </h3>

                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', paddingLeft: 12 }}>
                  {/* Vertical line using linear gradient to look like a path */}
                  <div style={{ position: 'absolute', left: 24, top: 0, bottom: 0, width: 2, background: 'linear-gradient(to bottom, #4f46e5, #9333ea, #4f46e5)', opacity: 0.3 }}></div>

                  {/* Steps */}
                  {traceData.steps.map((step, idx) => {
                    const isError = traceData.error_steps.includes(idx);
                    const isLast = idx === traceData.steps.length - 1;

                    return (
                      <div key={step.id} style={{ position: 'relative', paddingLeft: 48, paddingBottom: isLast ? 0 : 32 }}>
                        {/* Step number circle */}
                        <div style={{
                          position: 'absolute',
                          left: 0,
                          width: 44,
                          height: 44,
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          border: `2px solid ${isError ? '#ef4444' : '#4f46e5'}`,
                          background: isError ? '#fef2f2' : '#f5f3ff',
                          color: isError ? '#ef4444' : '#4f46e5',
                          zIndex: 1
                        }}>
                          {isError ? <AlertCircle size={20} /> : (idx + 1)}
                        </div>

                        {/* Step card */}
                        <div style={{
                          background: 'white',
                          borderRadius: 8,
                          border: `1px solid ${isError ? '#fecaca' : '#e2e8f0'}`,
                          overflow: 'hidden',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                        }}>
                          <div style={{ padding: 16, background: isError ? '#fffafb' : 'transparent' }}>
                            {/* Header */}
                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{
                                  padding: 6,
                                  borderRadius: 4,
                                  background: step.category === 'DB' ? '#eff6ff' :
                                    step.category === 'EXTERNAL' ? '#fff7ed' :
                                      step.category === 'HTTP' ? '#f0fdf4' :
                                        '#f8fafc',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center'
                                }}>
                                  {getCategoryIcon(step.category)}
                                </div>
                                <div>
                                  <span style={{
                                    fontSize: 9,
                                    fontWeight: 700,
                                    padding: '2px 6px',
                                    borderRadius: 4,
                                    background: isError ? '#fef2f2' : '#f1f5f9',
                                    color: isError ? '#dc2626' : '#64748b'
                                  }}>
                                    {step.level}
                                  </span>
                                  <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 8, fontWeight: 600 }}>
                                    {step.category}
                                  </span>
                                </div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <p style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace', margin: 0 }}>
                                  {new Date(step.timestamp).toLocaleTimeString()}
                                </p>
                                {step.duration_ms !== null && !isLast && (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#64748b', marginTop: 4, fontWeight: 700 }}>
                                    <Clock size={10} />
                                    <span>+{step.duration_ms}ms</span>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Message */}
                            <p style={{
                              fontSize: 12,
                              fontFamily: 'monospace',
                              lineHeight: 1.6,
                              margin: 0,
                              color: isError ? '#991b1b' : '#334155'
                            }}>
                              {step.message}
                            </p>

                            {/* Duration bar */}
                            {step.duration_ms !== null && !isLast && step.duration_ms > 0 && (
                              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f1f5f9' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 10, color: '#94a3b8' }}>
                                  <span style={{ fontWeight: 600 }}>Step Impact</span>
                                  <div style={{ flex: 1, height: 6, background: '#f1f5f9', borderRadius: 99, overflow: 'hidden' }}>
                                    <div
                                      style={{
                                        height: '100%',
                                        background: step.duration_ms > 1000 ? '#ef4444' :
                                          step.duration_ms > 500 ? '#f59e0b' :
                                            '#22c55e',
                                        width: `${Math.min((step.duration_ms / traceData.total_duration_ms) * 100, 100)}%`
                                      }}
                                    ></div>
                                  </div>
                                  <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#475569' }}>
                                    {((step.duration_ms / traceData.total_duration_ms) * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Error Summary */}
              {traceData.error_steps.length > 0 && (
                <div style={{ background: '#fff1f2', border: '1px solid #fecaca', borderRadius: 12, padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <AlertCircle size={18} color="#e11d48" />
                    <h4 style={{ fontSize: 14, fontWeight: 700, color: '#e11d48', margin: 0 }}>
                      Error Summary
                    </h4>
                  </div>
                  <p style={{ fontSize: 12, color: '#9f1239', margin: 0 }}>
                    {traceData.error_steps.length} error(s) detected in steps: {' '}
                    <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>
                      {traceData.error_steps.map(s => s + 1).join(', ')}
                    </span>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
