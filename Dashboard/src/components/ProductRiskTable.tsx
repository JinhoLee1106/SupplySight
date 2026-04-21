import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { DashboardProductRow } from '../types/dashboard';

const PLACEHOLDER_PRODUCTS = [
  { id: 'PRD-SALMON-001',    name: 'Salmon',    category: 'Seafood' },
  { id: 'PRD-TUNA-001',      name: 'Tuna',      category: 'Seafood' },
  { id: 'PRD-WHITEFISH-001', name: 'Whitefish', category: 'Seafood' },
];

function getRiskColor(level: string) {
  switch (level) {
    case 'Low':      return 'bg-green-100 text-green-700 border-green-200';
    case 'Medium':   return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'High':     return 'bg-orange-100 text-orange-700 border-orange-200';
    case 'Critical': return 'bg-red-100 text-red-700 border-red-200';
    default:         return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

// Trend is based on risk score direction; invert for SHI (higher SHI = better)
// 'up' means risk rising = SHI falling = bad → red downward arrow
// 'down' means risk falling = SHI rising = good → green upward arrow
function getTrendIcon(trend: string) {
  switch (trend) {
    case 'up':   return <TrendingDown className="w-3 h-3 text-red-500" />;
    case 'down': return <TrendingUp className="w-3 h-3 text-green-500" />;
    default:     return <Minus className="w-3 h-3 text-slate-400" />;
  }
}

function shiLabel(level: string) {
  switch (level) {
    case 'Low':      return 'Healthy';
    case 'Medium':   return 'Moderate';
    case 'High':     return 'At Risk';
    case 'Critical': return 'Critical';
    default:         return level;
  }
}

interface ProductRiskTableProps {
  products: DashboardProductRow[] | null;
  loading?: boolean;
}

export function ProductRiskTable({ products, loading }: ProductRiskTableProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg animate-pulse">
        <div className="p-5 border-b border-slate-200 space-y-2">
          <div className="h-5 w-48 bg-slate-100 rounded" />
          <div className="h-4 w-72 bg-slate-100 rounded" />
        </div>
        <div className="p-5 h-40 bg-slate-50" />
      </div>
    );
  }

  const rows = products ?? [];

  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="p-5 border-b border-slate-200">
        <h2 className="text-slate-900 mb-1">Product Supply Health Forecasts</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-5 py-3 text-slate-700 text-sm font-medium">Product</th>
              <th className="text-left px-5 py-3 text-slate-700 text-sm font-medium">Category</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">30 Days</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">60 Days</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">90 Days</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && PLACEHOLDER_PRODUCTS.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-slate-500 text-sm">
                  No product data available.
                </td>
              </tr>
            ) : (
              <>
                {rows.map((product) => (
                  <tr key={product.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="text-slate-900 font-medium text-sm">{product.name}</div>
                      <div className="text-slate-500 text-xs">{product.id}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-slate-700 text-sm">{product.category}</span>
                    </td>
                    {([product.risk30, product.risk60, product.risk90] as const).map((horizon, i) => (
                      <td key={i} className="px-5 py-4">
                        <div className="flex items-center justify-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(horizon.level)}`}>
                            {shiLabel(horizon.level)}
                          </span>
                          <span className="text-slate-600 text-xs" title="Supply Health Index">
                            {((100 - horizon.score) / 10).toFixed(1)}
                          </span>
                          {getTrendIcon(horizon.trend)}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}

                {PLACEHOLDER_PRODUCTS.map((product) => (
                  <tr key={product.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="text-slate-900 font-medium text-sm">{product.name}</div>
                      <div className="text-slate-500 text-xs">{product.id}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-slate-700 text-sm">{product.category}</span>
                    </td>
                    {[0, 1, 2].map((i) => (
                      <td key={i} className="px-5 py-4">
                        <div className="flex items-center justify-center gap-2">
                          <span className="px-2 py-1 rounded text-xs font-medium border bg-slate-100 text-slate-400 border-slate-200">
                            —
                          </span>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
