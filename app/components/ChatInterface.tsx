import { useState, useRef, useEffect } from 'react';
import { getApiConfig } from '@/lib/config';
import { Send, Bot, User, Sparkles, Clock, Calendar, X } from 'lucide-react';

interface Finding {
  what: string;
  when: string;
  why: string;
  how: string;
  recommendation: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  findings?: Finding[];
  timePeriod?: string;
  logsAnalyzed?: number;
  customTimeRange?: {
    start: string;
    end: string;
  };
}

interface Props {
  logs: any[];
  timeFilter: string;
}

interface AnalyzeRequest {
  input: string;
  time_filter?: string;
  custom_start?: number;
  custom_end?: number;
  history?: { role: string, content: string }[];
}

export function ChatInterface({ timeFilter }: Props) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Ask me about the logs! I can analyze data from specific time periods. Click the calendar icon to select a custom time range.'
    }
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [customTimeRange, setCustomTimeRange] = useState<{ start: string, end: string } | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    setEndDate(formatDateForInput(now));
    setEndTime(formatTimeForInput(now));
    setStartDate(formatDateForInput(yesterday));
    setStartTime(formatTimeForInput(yesterday));
  }, []);

  const formatDateForInput = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  const formatTimeForInput = (date: Date) => {
    return date.toTimeString().slice(0, 5);
  };

  const handleApplyCustomTime = () => {
    if (!startDate || !startTime || !endDate || !endTime) {
      alert('Please select both start and end date/time');
      return;
    }

    const start = new Date(`${startDate}T${startTime}`).toISOString();
    const end = new Date(`${endDate}T${endTime}`).toISOString();

    setCustomTimeRange({ start, end });
    setShowDatePicker(false);

    const systemMsg: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `Custom time range applied: ${new Date(start).toLocaleString()} to ${new Date(end).toLocaleString()}.`,
      customTimeRange: { start, end }
    };
    setMessages(prev => [...prev, systemMsg]);
  };

  const clearCustomTimeRange = () => {
    setCustomTimeRange(null);
    const systemMsg: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `Custom time range cleared. Now using default filter: ${timeFilter}.`
    };
    setMessages(prev => [...prev, systemMsg]);
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    };
    
    // Capture history BEFORE adding the new message
    const history = messages.map(m => ({
      role: m.role,
      content: m.content
    })).filter(m => m.content !== 'Ask me about the logs! I can analyze data from specific time periods. Click the calendar icon to select a custom time range.');

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const requestBody: AnalyzeRequest = { 
        input,
        history 
      };

      if (customTimeRange) {
        const startTimestamp = new Date(customTimeRange.start).getTime();
        const endTimestamp = new Date(customTimeRange.end).getTime();
        requestBody.custom_start = startTimestamp;
        requestBody.custom_end = endTimestamp;
      } else {
        requestBody.time_filter = timeFilter;
      }

      const { apiBaseUrl, apiKey } = getApiConfig();
      const res = await fetch(`${apiBaseUrl}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(requestBody),
      });

      const data = await res.json();
      const aiMsg: Message = {
        id: Date.now().toString() + '_ai',
        role: 'assistant',
        content: data.summary,
        findings: data.findings,
        timePeriod: data.time_period,
        logsAnalyzed: data.logs_analyzed,
        customTimeRange: customTimeRange || undefined
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) { // eslint-disable-line @typescript-eslint/no-unused-vars
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Failed to get AI response. Please check if the backend is running.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickTimeRanges = [
    { label: 'Last Hour', hours: 1 },
    { label: '3 Hours', hours: 3 },
    { label: '6 Hours', hours: 6 },
    { label: '12 Hours', hours: 12 },
    { label: 'Today', hours: 24 },
  ];

  const handleQuickRange = (hours: number) => {
    const now = new Date();
    const past = new Date(now.getTime() - hours * 60 * 60 * 1000);
    setStartDate(formatDateForInput(past));
    setStartTime(formatTimeForInput(past));
    setEndDate(formatDateForInput(now));
    setEndTime(formatTimeForInput(now));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: 'white' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid #e2e8f0' }}>
        <Sparkles size={18} color="#4f46e5" />
        <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: 0 }}>Log Assistant</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {customTimeRange ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#eef2ff', border: '1px solid #c7d2fe', borderRadius: 6, padding: '2px 8px' }}>
              <Clock size={10} color="#4338ca" />
              <span style={{ fontSize: 10, color: '#4338ca', fontWeight: 600 }}>Custom Range</span>
              <button onClick={clearCustomTimeRange} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}>
                <X size={10} color="#4338ca" />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#94a3b8', fontWeight: 600 }}>
              <Clock size={10} />
              <span>{timeFilter}</span>
            </div>
          )}
          <button
            onClick={() => setShowDatePicker(!showDatePicker)}
            style={{
              padding: 6,
              borderRadius: 6,
              border: 'none',
              cursor: 'pointer',
              background: showDatePicker ? '#4f46e5' : '#f1f5f9',
              color: showDatePicker ? 'white' : '#64748b'
            }}
          >
            <Calendar size={14} />
          </button>
        </div>
      </div>

      {/* Custom Date/Time Picker */}
      {showDatePicker && (
        <div style={{ borderBottom: '1px solid #e2e8f0', background: '#f8fafc', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <h4 style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', margin: 0, flex: 1 }}>Select Time Range</h4>
            <button onClick={() => setShowDatePicker(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
              <X size={14} />
            </button>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {quickTimeRanges.map((range) => (
              <button
                key={range.label}
                onClick={() => handleQuickRange(range.hours)}
                style={{ padding: '4px 8px', fontSize: 10, background: 'white', border: '1px solid #e2e8f0', borderRadius: 4, cursor: 'pointer', fontWeight: 600, color: '#475569' }}
              >
                {range.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 10, color: '#64748b', fontWeight: 700 }}>Start</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ padding: '6px 8px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 12, outline: 'none' }} />
              <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} style={{ padding: '6px 8px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 12, outline: 'none' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 10, color: '#64748b', fontWeight: 700 }}>End</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ padding: '6px 8px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 12, outline: 'none' }} />
              <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} style={{ padding: '6px 8px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 12, outline: 'none' }} />
            </div>
          </div>

          <button
            onClick={handleApplyCustomTime}
            style={{ width: '100%', background: '#4f46e5', color: 'white', padding: '8px', borderRadius: 6, border: 'none', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}
          >
            Apply Custom Range
          </button>
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }} ref={scrollRef}>
        {messages.map(m => (
          <div key={m.id} style={{ display: 'flex', gap: 10, flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              background: m.role === 'assistant' ? '#eff6ff' : '#f5f3ff',
              color: m.role === 'assistant' ? '#2563eb' : '#7c3aed'
            }}>
              {m.role === 'assistant' ? <Bot size={14} /> : <User size={14} />}
            </div>
            <div style={{
              maxWidth: '85%',
              borderRadius: 12,
              padding: 12,
              fontSize: 12,
              lineHeight: 1.5,
              background: m.role === 'assistant' ? '#f1f5f9' : '#4f46e5',
              color: m.role === 'assistant' ? '#1e293b' : 'white',
              borderTopLeftRadius: m.role === 'assistant' ? 2 : 12,
              borderTopRightRadius: m.role === 'user' ? 2 : 12
            }}>
              <p style={{ margin: 0 }}>{m.content}</p>

              {m.customTimeRange && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${m.role === 'user' ? 'rgba(255,255,255,0.1)' : '#e2e8f0'}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: m.role === 'user' ? '#e0e7ff' : '#64748b' }}>
                    <Calendar size={10} />
                    <span>
                      {new Date(m.customTimeRange.start).toLocaleString()} -{' '}
                      {new Date(m.customTimeRange.end).toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              {m.timePeriod && m.logsAnalyzed !== undefined && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #e2e8f0', fontSize: 10, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Clock size={10} />
                    <span>{m.timePeriod}</span>
                  </div>
                  <div>📊 Analyzed {m.logsAnalyzed.toLocaleString()} log entries</div>
                </div>
              )}

              {m.findings && m.findings.length > 0 && (
                <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {m.findings.map((f, i) => (
                    <div key={i} style={{ background: 'white', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', color: '#1e293b' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr', gap: '6px 12px', fontSize: 11 }}>
                        <div style={{ fontWeight: 700, color: '#94a3b8' }}>What:</div>
                        <div>{f.what}</div>
                        <div style={{ fontWeight: 700, color: '#94a3b8' }}>Why:</div>
                        <div>{f.why}</div>
                        <div style={{ fontWeight: 700, color: '#16a34a' }}>Action:</div>
                        <div style={{ fontWeight: 600, color: '#16a34a' }}>{f.recommendation}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#94a3b8', fontSize: 11, fontStyle: 'italic' }}>
            <div style={{ width: 12, height: 12, border: '2px solid #e2e8f0', borderTopColor: '#4f46e5', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            AI is analyzing logs...
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ padding: 16, borderTop: '1px solid #e2e8f0', background: 'white' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={customTimeRange ? "Ask about custom range..." : "Ask about your logs..."}
            style={{
              flex: 1,
              background: '#f1f5f9',
              border: '1px solid #e2e8f0',
              borderRadius: 8,
              padding: '8px 12px',
              fontSize: 12,
              color: '#0f172a',
              outline: 'none'
            }}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading}
            style={{
              padding: 8,
              background: '#4f46e5',
              border: 'none',
              borderRadius: 8,
              color: 'white',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: loading ? 0.5 : 1
            }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
