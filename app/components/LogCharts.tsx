'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';

interface RequestsByHour {
  hour: string;
  count: number;
  errors: number;
}

interface StatusCode {
  code: string;
  count: number;
}

interface RequestVolumeChartProps {
  data: RequestsByHour[];
  onBarClick?: (category: string) => void;
}

interface StatusCodeChartProps {
  data: StatusCode[];
  onBarClick?: (category: string) => void;
}

export function RequestVolumeChart({
  data,
  onBarClick
}: RequestVolumeChartProps) {
  const handleClick = (chartState: { activeLabel?: string | number } | null) => {
    if (onBarClick && chartState?.activeLabel !== undefined) {
      onBarClick('time_' + chartState.activeLabel);
    }
  };

  return (
    <div style={{ height: 280, width: '100%', background: 'white', padding: 0 }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: '0 0 16px 0' }}>
        Request Volume Over Time
        <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 8, fontWeight: 400 }}>(Click bars to drill down)</span>
      </h3>
      <div style={{ height: 'calc(100% - 30px)', width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} onClick={handleClick} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorError" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="hour"
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '11px',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
              }}
              labelStyle={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}
              itemStyle={{ padding: '2px 0' }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#2563eb"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorCount)"
              name="Requests"
              style={{ cursor: 'pointer' }}
            />
            <Area
              type="monotone"
              dataKey="errors"
              stroke="#ef4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorError)"
              name="Errors"
              style={{ cursor: 'pointer' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function StatusCodeChart({
  data,
  onBarClick
}: StatusCodeChartProps) {
  const sortedData = [...data].sort((a, b) => b.count - a.count);

  const handleClick = (entry: { payload?: StatusCode }) => {
    if (onBarClick && entry.payload) {
      onBarClick('status_' + entry.payload.code);
    }
  };

  return (
    <div style={{ height: 280, width: '100%', background: 'white', padding: 0 }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', margin: '0 0 16px 0' }}>
        Status Distribution
        <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 8, fontWeight: 400 }}>(Click to filter)</span>
      </h3>
      <div style={{ height: 'calc(100% - 30px)', width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sortedData} layout="vertical" margin={{ top: 0, right: 20, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#e2e8f0"
              horizontal={false}
            />
            <XAxis
              type="number"
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              dataKey="code"
              type="category"
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              width={60}
            />
            <Tooltip
              cursor={{ fill: '#f8fafc' }}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '11px',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
              }}
            />
            <Bar
              dataKey="count"
              radius={[0, 4, 4, 0]}
              onClick={handleClick}
              style={{ cursor: 'pointer' }}
              barSize={20}
            >
              {sortedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.code.startsWith('2') ? '#16a34a' :
                      entry.code.startsWith('4') || entry.code.startsWith('5') ? '#dc2626' :
                        '#d97706'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
