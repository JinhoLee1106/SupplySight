import { useState } from 'react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts';
import type { TrendPointDTO } from '../types/dashboard';

interface TrendVisualizationProps {
  points: TrendPointDTO[] | null;
  loading?: boolean;
}

type View = 'risk' | 'imports' | 'price';

const VIEWS: { key: View; label: string }[] = [
  { key: 'risk', label: 'Risk Score' },
  { key: 'imports', label: 'Monthly Imports' },
  { key: 'price', label: 'Price Index' },
];

function fmtImport(v: number) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M lbs`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K lbs`;
  return `${v} lbs`;
}

function riskLabel(score: number) {
  if (score >= 75) return 'Critical';
  if (score >= 50) return 'High';
  if (score >= 25) return 'Medium';
  return 'Low';
}

export function TrendVisualization({ points, loading }: TrendVisualizationProps) {
  const [view, setView] = useState<View>('risk');

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg animate-pulse">
        <div className="p-5 border-b border-slate-200 space-y-2">
          <div className="h-5 w-56 bg-slate-100 rounded" />
          <div className="h-4 w-80 bg-slate-100 rounded" />
        </div>
        <div className="p-5 h-[320px] bg-slate-50" />
      </div>
    );
  }

  const data = (points ?? []).map((p) => ({
    date: p.date,
    risk: p.shrimp,
    imports: p.monthlyImport ?? undefined,
    price: p.priceIndex ?? undefined,
  }));

  // Only show every 6th x-axis tick to avoid crowding
  const xTicks = data
    .map((d) => d.date)
    .filter((_, i) => i % 6 === 0);

  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="p-5 border-b border-slate-200 flex items-start justify-between">
        <div>
          <h2 className="text-slate-900 mb-1">Risk Trends Over Time</h2>
          <p className="text-slate-600 text-sm">
            Monthly supply risk based on import volume and price index
          </p>
        </div>
        <div className="flex gap-1">
          {VIEWS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                view === key
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'text-slate-600 border-slate-200 hover:border-blue-300 hover:bg-slate-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        {data.length === 0 ? (
          <div className="h-[320px] flex items-center justify-center text-slate-500 text-sm border border-dashed border-slate-200 rounded-lg">
            No trend data available.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={data} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                ticks={xTicks}
                stroke="#64748b"
                style={{ fontSize: '11px' }}
              />

              {view === 'risk' && (
                <>
                  <YAxis domain={[0, 100]} stroke="#64748b" style={{ fontSize: '11px' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px' }}
                    formatter={(value: number) => [`${value} — ${riskLabel(value)}`, 'Risk Score']}
                  />
                  <Line type="monotone" dataKey="risk" name="Risk Score" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 4 }} />
                </>
              )}

              {view === 'imports' && (
                <>
                  <YAxis stroke="#64748b" style={{ fontSize: '11px' }} tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px' }}
                    formatter={(value: number) => [fmtImport(value), 'Monthly Import']}
                  />
                  <Bar dataKey="imports" name="Monthly Import" fill="#3b82f6" opacity={0.8} radius={[2, 2, 0, 0]} />
                </>
              )}

              {view === 'price' && (
                <>
                  <YAxis stroke="#64748b" style={{ fontSize: '11px' }} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px' }}
                    formatter={(value: number) => [value.toFixed(1), 'Price Index']}
                  />
                  <Line type="monotone" dataKey="price" name="Price Index" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 4 }} connectNulls={false} />
                </>
              )}

              <Legend wrapperStyle={{ fontSize: '12px' }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
