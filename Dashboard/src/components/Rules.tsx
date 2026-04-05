import { Shield, Plus } from 'lucide-react';

export function Rules() {
  const rules = [
    {
      id: 1,
      name: 'High Risk Threshold',
      description: 'Alert when product risk score exceeds 20',
      status: 'Active',
      category: 'Risk Management',
    },
    {
      id: 2,
      name: 'Supplier Diversification',
      description: 'Flag products with single supplier dependency',
      status: 'Active',
      category: 'Supply Chain',
    },
    {
      id: 3,
      name: 'Price Volatility Monitor',
      description: 'Track price changes exceeding 15% within 30 days',
      status: 'Active',
      category: 'Financial',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-slate-900 mb-1">Rules</h1>
          <p className="text-slate-600">Configure automated risk management rules</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4" />
          Add Rule
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {rules.map((rule) => (
          <div key={rule.id} className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="bg-blue-50 p-3 rounded-lg">
                <Shield className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-slate-900 font-medium mb-1">{rule.name}</h3>
                    <p className="text-slate-600 text-sm">{rule.description}</p>
                  </div>
                  <span className="px-3 py-1 bg-green-50 text-green-700 text-xs font-medium rounded-full border border-green-200">
                    {rule.status}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-3">
                  Category: {rule.category}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
