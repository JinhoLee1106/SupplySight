import { RiskOverview } from './RiskOverview';
import { ProductRiskTable } from './ProductRiskTable';
import { TrendVisualization } from './TrendVisualization';
import { EvidencePanel } from './EvidencePanel';
import { DecisionSupportPanel } from './DecisionSupportPanel';
import { useDashboard } from '../hooks/useDashboard';

export function Dashboard() {
  const { data, loading, error } = useDashboard();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-slate-900 mb-1">Risk Dashboard</h1>
        <p className="text-slate-600">Monitor and forecast supply chain risks across your product portfolio</p>
        {error && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error} — start API:{' '}
            <code className="text-xs bg-red-100 px-1 py-0.5 rounded">
              uvicorn services.api.main:app --reload --port 8000
            </code>{' '}
            from repo root (with Postgres env vars set).
          </div>
        )}
        {data?.meta?.usingPlaceholders && (
          <div
            className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            role="status"
          >
            <span className="font-medium">Placeholder data</span>
            {data.meta.placeholderReason && (
              <span className="text-amber-900"> — {data.meta.placeholderReason.replace(/_/g, ' ')}</span>
            )}
            {data.meta.placeholderSections?.length ? (
              <span className="block text-xs text-amber-900 mt-1">
                Sections: {data.meta.placeholderSections.join(', ')}
              </span>
            ) : null}
            {data.meta.dbError && (
              <span className="block text-xs text-amber-900 mt-1 font-mono break-all">{data.meta.dbError}</span>
            )}
          </div>
        )}
        {data?.meta && (
          <p className="text-slate-500 text-xs mt-2">
            Data as of: {data.meta.asOf ?? '—'} · Generated: {data.meta.generatedAt}
            {!data.meta.hasData && ' · No live rows in months_shrimp (showing samples)'}
          </p>
        )}
      </div>

      <RiskOverview metrics={data?.overview ?? null} loading={loading} />

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <ProductRiskTable products={data?.products ?? null} loading={loading} />
          <TrendVisualization points={data?.trend ?? null} loading={loading} />
        </div>

        <div className="col-span-1 space-y-6">
          <EvidencePanel items={data?.evidence ?? null} loading={loading} />
          <DecisionSupportPanel recommendations={data?.recommendations ?? null} loading={loading} />
        </div>
      </div>
    </div>
  );
}
