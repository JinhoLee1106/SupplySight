import { Link } from 'react-router';
import { AlertTriangle, Package, Bell } from 'lucide-react';
import type { OverviewMetricDTO } from '../types/dashboard';

function riskStyles(value: string) {
  const v = value.toLowerCase();
  if (v.includes('critical'))
    return {
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
    };
  if (v.includes('high'))
    return {
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
    };
  if (v.includes('medium'))
    return {
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
    };
  if (v.includes('low'))
    return {
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
    };
  return {
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
  };
}

function metricVisual(metric: OverviewMetricDTO) {
  if (metric.key === 'risk') {
    const s = riskStyles(metric.value);
    return { Icon: AlertTriangle, ...s };
  }
  if (metric.key === 'alerts') {
    return {
      Icon: Bell,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
    };
  }
  return {
    Icon: Package,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  };
}

interface RiskOverviewProps {
  metrics: OverviewMetricDTO[] | null;
  loading?: boolean;
}

export function RiskOverview({ metrics, loading }: RiskOverviewProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-lg p-5 animate-pulse">
            <div className="h-9 w-9 bg-slate-100 rounded-lg mb-3" />
            <div className="h-4 w-32 bg-slate-100 rounded mb-2" />
            <div className="h-8 w-20 bg-slate-100 rounded mb-2" />
            <div className="h-3 w-full bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (!metrics?.length) {
    return (
      <div className="bg-white border border-dashed border-slate-200 rounded-lg p-6 text-slate-600 text-sm">
        No overview metrics (database may be empty or unreachable).
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {metrics.map((metric) => {
        const { Icon, color, bgColor, borderColor } = metricVisual(metric);
        const inner = (
          <>
            <div className="flex items-start justify-between mb-3">
              <div className={`${bgColor} p-2 rounded-lg`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              {metric.key === 'risk' && (
                <span className="text-xs text-slate-400 font-medium">View model ›</span>
              )}
            </div>
            <div className="space-y-1">
              <p className="text-slate-600 text-sm">{metric.label}</p>
              <p className={`text-3xl font-semibold ${color}`}>{metric.value}</p>
              <p className="text-slate-500 text-xs">{metric.subtext}</p>
            </div>
          </>
        );

        if (metric.key === 'risk') {
          return (
            <Link
              key={metric.key}
              to="/rules"
              className={`bg-white border ${borderColor} rounded-lg p-5 block hover:shadow-md transition-shadow cursor-pointer`}
            >
              {inner}
            </Link>
          );
        }

        return (
          <div key={metric.key} className={`bg-white border ${borderColor} rounded-lg p-5`}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}
