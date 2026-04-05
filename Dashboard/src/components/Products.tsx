import { ProductRiskTable } from './ProductRiskTable';
import { useDashboard } from '../hooks/useDashboard';

export function Products() {
  const { data, loading } = useDashboard();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-slate-900 mb-1">Products</h1>
        <p className="text-slate-600">Supply risk forecast by product across 30, 60, and 90-day horizons</p>
      </div>
      <ProductRiskTable products={data?.products ?? null} loading={loading} />
    </div>
  );
}
