import { Database as DatabaseIcon, Search, Filter, Download } from 'lucide-react';

export function Database() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-slate-900 mb-1">Database</h1>
        <p className="text-slate-600">Access and manage supply chain data</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search database..."
              className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 transition-colors">
            <Filter className="w-4 h-4" />
            Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>

        <div className="text-center py-12 text-slate-500">
          <DatabaseIcon className="w-12 h-12 mx-auto mb-3 text-slate-400" />
          <p>Database interface</p>
        </div>
      </div>
    </div>
  );
}
