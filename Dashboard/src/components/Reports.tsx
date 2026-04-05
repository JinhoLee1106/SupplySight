import { FileText, Download, Calendar, TrendingUp } from 'lucide-react';

export function Reports() {
  const reports = [
    {
      title: 'Monthly Risk Assessment',
      description: 'Comprehensive risk analysis for all monitored products',
      date: 'March 2026',
      type: 'Monthly Report',
    },
    {
      title: 'Supplier Performance Review',
      description: 'Evaluation of supplier reliability and risk factors',
      date: 'Q1 2026',
      type: 'Quarterly Report',
    },
    {
      title: 'Cost Impact Analysis',
      description: 'Financial impact of supply chain disruptions',
      date: 'February 2026',
      type: 'Custom Report',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-slate-900 mb-1">Reports</h1>
          <p className="text-slate-600">Generate and download supply chain risk reports</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
          Generate New Report
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {reports.map((report, index) => (
          <div key={index} className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="bg-blue-50 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-slate-900 font-medium mb-1">{report.title}</h3>
                <p className="text-slate-600 text-sm mb-3">{report.description}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {report.date}
                  </div>
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    {report.type}
                  </div>
                </div>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 transition-colors">
                <Download className="w-4 h-4" />
                Download
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
