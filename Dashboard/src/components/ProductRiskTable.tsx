import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { DashboardProductRow } from '../types/dashboard';

function getRiskColor(level: string) {
  switch (level) {
    case 'Low':
      return 'bg-green-100 text-green-700 border-green-200';
    case 'Medium':
      return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'High':
      return 'bg-orange-100 text-orange-700 border-orange-200';
    case 'Critical':
      return 'bg-red-100 text-red-700 border-red-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

function getTrendIcon(trend: string) {
  switch (trend) {
    case 'up':
      return <TrendingUp className="w-3 h-3 text-red-500" />;
    case 'down':
      return <TrendingDown className="w-3 h-3 text-green-500" />;
    default:
      return <Minus className="w-3 h-3 text-slate-400" />;
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
        <h2 className="text-slate-900 mb-1">Product Risk Forecasts</h2>
        <p className="text-slate-600 text-sm">
          Predicted risk levels across 30, 60, and 90-day horizons
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-5 py-3 text-slate-700 text-sm font-medium">Product</th>
              <th className="text-left px-5 py-3 text-slate-700 text-sm font-medium">Category</th>
              <th className="text-left px-5 py-3 text-slate-700 text-sm font-medium">Supplier</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">30 Days</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">60 Days</th>
              <th className="text-center px-5 py-3 text-slate-700 text-sm font-medium">90 Days</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-slate-500 text-sm">
                  No product data available.
                </td>
              </tr>
            ) : (
              rows.map((product) => (
                <tr key={product.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-5 py-4">
                    <div>
                      <div className="text-slate-900 font-medium text-sm">{product.name}</div>
                      <div className="text-slate-500 text-xs">{product.id}</div>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-slate-700 text-sm">{product.category}</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-slate-700 text-sm">{product.supplier}</span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(product.risk30.level)}`}>
                        {product.risk30.level}
                      </span>
                      <span className="text-slate-600 text-xs">{product.risk30.score}</span>
                      {getTrendIcon(product.risk30.trend)}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(product.risk60.level)}`}>
                        {product.risk60.level}
                      </span>
                      <span className="text-slate-600 text-xs">{product.risk60.score}</span>
                      {getTrendIcon(product.risk60.trend)}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(product.risk90.level)}`}>
                        {product.risk90.level}
                      </span>
                      <span className="text-slate-600 text-xs">{product.risk90.score}</span>
                      {getTrendIcon(product.risk90.trend)}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
