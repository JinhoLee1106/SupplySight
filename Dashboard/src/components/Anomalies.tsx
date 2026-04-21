import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';

const LABEL_MAP: Record<string, string> = {
  price_index_value: 'Price Index',
  oil_price: 'Oil Price',
  sentiment_score: 'Sentiment Score',
  import_volume: 'Import Volume',
  relevancy_score: 'Relevancy Score',
};

function humanize(key: string): string {
  return LABEL_MAP[key] ?? key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function severity(z: number): { label: string; bg: string; text: string; border: string } {
  const abs = Math.abs(z);
  if (abs >= 2.5) return { label: 'Critical', bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-200' };
  if (abs >= 2)   return { label: 'High',     bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' };
  return              { label: 'Moderate',  bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' };
}

interface Props {
  anomalies: Record<string, number> | undefined;
  loading: boolean;
}

export function AnomalyPanel({ anomalies, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <div className="h-5 bg-slate-200 rounded w-40 animate-pulse" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  const entries = Object.entries(anomalies ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-700">Anomalies</h2>
        <span className="text-xs text-slate-400 ml-1">— 60-day avg vs 3-year baseline</span>
      </div>

      {entries.length === 0 ? (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <CheckCircle className="w-4 h-4 shrink-0" />
          No significant anomalies in the past 60 days.
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, z]) => {
            const { label, bg, text, border } = severity(z);
            const above = z > 0;
            return (
              <div key={key} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${bg} ${border}`}>
                {above
                  ? <TrendingUp className={`w-4 h-4 shrink-0 ${text}`} />
                  : <TrendingDown className={`w-4 h-4 shrink-0 ${text}`} />
                }
                <span className={`flex-1 text-sm font-medium text-slate-800`}>{humanize(key)}</span>
                <span className={`text-xs ${text}`}>{above ? 'above' : 'below'} avg</span>
                <span className={`text-sm font-semibold tabular-nums ${text}`}>
                  {z > 0 ? '+' : ''}{z.toFixed(2)}σ
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${bg} ${text} ${border}`}>
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
