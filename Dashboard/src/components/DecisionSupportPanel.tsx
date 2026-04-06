import { ShoppingCart, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import type { RecommendationDTO, RecommendationIconType } from '../types/dashboard';

function iconFor(type: RecommendationIconType) {
  switch (type) {
    case 'cart':
      return ShoppingCart;
    case 'refresh':
      return RefreshCw;
    case 'clock':
      return Clock;
    case 'alert':
    default:
      return AlertCircle;
  }
}

function getPriorityColor(priority: string) {
  switch (priority) {
    case 'High':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'Medium':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'Low':
      return 'text-green-600 bg-green-50 border-green-200';
    default:
      return 'text-slate-600 bg-slate-50 border-slate-200';
  }
}

interface DecisionSupportPanelProps {
  recommendations: RecommendationDTO[] | null;
  loading?: boolean;
}

export function DecisionSupportPanel({ recommendations, loading }: DecisionSupportPanelProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg animate-pulse">
        <div className="p-5 border-b border-slate-200 space-y-2">
          <div className="h-5 w-40 bg-slate-100 rounded" />
          <div className="h-4 w-64 bg-slate-100 rounded" />
        </div>
        <div className="p-4 space-y-3">
          <div className="h-36 bg-slate-50 rounded-lg" />
        </div>
      </div>
    );
  }

  const recs = recommendations ?? [];

  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="p-5 border-b border-slate-200">
        <h2 className="text-slate-900 mb-1">Decision Support</h2>
        <p className="text-slate-600 text-sm">Suggested actions based on current supply risk signals</p>
      </div>
      <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
        {recs.length === 0 ? (
          <p className="text-slate-500 text-sm px-1">No recommendations for current data.</p>
        ) : (
          recs.map((rec, index) => {
            const Icon = iconFor(rec.iconType);
            return (
              <div key={index} className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="bg-blue-50 p-2 rounded-lg flex-shrink-0">
                    <Icon className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h3 className="text-slate-900 text-sm font-medium">{rec.action}</h3>
                        <p className="text-blue-600 text-xs">{rec.product}</p>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border flex-shrink-0 ${getPriorityColor(rec.priority)}`}>
                        {rec.priority}
                      </span>
                    </div>
                    <p className="text-slate-600 text-xs mb-3 leading-relaxed">{rec.description}</p>
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                        <span className="text-green-700 text-xs font-medium">{rec.savings}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                        <span className="text-slate-600 text-xs">{rec.timeline}</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white text-xs py-2 px-3 rounded-lg transition-colors"
                    >
                      Take Action
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
