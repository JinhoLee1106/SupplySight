import { FileText, Globe, TrendingUp, MapPin } from 'lucide-react';
import type { EvidenceItemDTO, EvidenceIconType, EvidenceIconColor } from '../types/dashboard';

function iconFor(type: EvidenceIconType) {
  switch (type) {
    case 'globe':
      return Globe;
    case 'trending':
      return TrendingUp;
    case 'map':
      return MapPin;
    case 'file':
    default:
      return FileText;
  }
}

function getIconStyle(color?: EvidenceIconColor) {
  if (color === 'green') return { bg: 'bg-green-50', icon: 'text-green-600' };
  if (color === 'red') return { bg: 'bg-red-50', icon: 'text-red-600' };
  return { bg: 'bg-blue-50', icon: 'text-blue-600' };
}

function getImpactColor(impact: string) {
  switch (impact) {
    case 'Critical':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'High':
      return 'text-orange-600 bg-orange-50 border-orange-200';
    case 'Medium':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    default:
      return 'text-slate-600 bg-slate-50 border-slate-200';
  }
}

interface EvidencePanelProps {
  items: EvidenceItemDTO[] | null;
  loading?: boolean;
}

export function EvidencePanel({ items, loading }: EvidencePanelProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg animate-pulse">
        <div className="p-5 border-b border-slate-200 space-y-2">
          <div className="h-5 w-36 bg-slate-100 rounded" />
          <div className="h-4 w-52 bg-slate-100 rounded" />
        </div>
        <div className="p-4 space-y-3">
          <div className="h-24 bg-slate-50 rounded-lg" />
          <div className="h-24 bg-slate-50 rounded-lg" />
        </div>
      </div>
    );
  }

  const evidenceItems = items ?? [];

  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="p-5 border-b border-slate-200">
        <h2 className="text-slate-900 mb-1">Relevant News</h2>
        <p className="text-slate-600 text-sm">
          click any article to read the source
        </p>
      </div>
      <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
        {evidenceItems.length === 0 ? (
          <p className="text-slate-500 text-sm px-1">No news articles available.</p>
        ) : (
          evidenceItems.map((item, index) => {
            const Icon = iconFor(item.iconType);
            const { bg, icon } = getIconStyle(item.iconColor);
            const Tag = item.url ? 'a' : 'div';
            const linkProps = item.url
              ? { href: item.url, target: '_blank', rel: 'noopener noreferrer' }
              : {};
            return (
              <Tag key={index} {...linkProps} className="block">
                <div className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:bg-slate-50 transition-colors cursor-pointer">
                  <div className="flex items-start gap-3">
                    <div className={`${bg} p-2 rounded-lg flex-shrink-0`}>
                      <Icon className={`w-4 h-4 ${icon}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h3 className="text-slate-900 text-sm font-medium leading-snug">{item.title}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium border flex-shrink-0 ${getImpactColor(item.impact)}`}>
                          {item.impact}
                        </span>
                      </div>
                      <p className="text-slate-600 text-xs mb-2 leading-relaxed">{item.description}</p>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-blue-600">{item.source}</span>
                        <div className="flex items-center gap-2 text-slate-500">
                          <span>{item.date}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </Tag>
            );
          })
        )}
      </div>
    </div>
  );
}
