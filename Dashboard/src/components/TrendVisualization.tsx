import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { TrendPointDTO } from '../types/dashboard';

interface TrendVisualizationProps {
  points: TrendPointDTO[] | null;
  loading?: boolean;
}

/**
 * Chart Y-axis: heuristic risk score derived from `monthly_import_zscore_6` (see API).
 * UNCERTAIN: Tooltip also shows raw `monthlyImport` / `priceIndex` when present — confirm units with pipeline owners.
 */
export function TrendVisualization({ points, loading }: TrendVisualizationProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg animate-pulse">
        <div className="p-5 border-b border-slate-200 space-y-2">
          <div className="h-5 w-56 bg-slate-100 rounded" />
          <div className="h-4 w-80 bg-slate-100 rounded" />
        </div>
        <div className="p-5 h-[300px] bg-slate-50" />
      </div>
    );
  }

  const data = (points ?? []).map((p) => ({
    date: p.date,
    shrimp: p.shrimp,
    monthlyImport: p.monthlyImport ?? undefined,
    priceIndex: p.priceIndex ?? undefined,
  }));

  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="p-5 border-b border-slate-200 flex items-start justify-between">
        <div>
          <h2 className="text-slate-900 mb-1">Risk Trends Over Time</h2>
          <p className="text-slate-600 text-sm">
            Heuristic score from import z-score (monthly); not multi-product in current schema
          </p>
        </div>
      </div>
      <div className="p-5">
        {data.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm border border-dashed border-slate-200 rounded-lg">
            No trend points — populate `months_shrimp` or fix API.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#64748b" style={{ fontSize: '12px' }} />
              <YAxis
                stroke="#64748b"
                style={{ fontSize: '12px' }}
                label={{ value: 'Heuristic risk', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
                formatter={(value: number, name: string) => {
                  if (name === 'monthlyImport') return [value, 'monthly_import (raw)'];
                  if (name === 'priceIndex') return [value, 'FAO price index'];
                  return [value, name];
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line type="monotone" dataKey="shrimp" name="Shrimp (heuristic)" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
