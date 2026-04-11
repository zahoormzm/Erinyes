import { Fragment, useState } from 'react';

export default function AgentTrace({ data = [], emptyMessage = null, title = null }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="glass-card p-6 overflow-x-auto">
      {title ? <div className="font-semibold text-slate-900 mb-4">{title}</div> : null}
      {!data.length && (
        <div className="empty-state-card mb-4 px-4 py-4 text-sm text-slate-500">
          {emptyMessage || 'No stored agent traces yet. Use Coach, Mental Health, Future Self, uploads that invoke agents, or wait for live model calls below.'}
        </div>
      )}
      <table className="w-full">
        <thead>
          <tr>
            {['Timestamp', 'Agent', 'Tool', 'Model', 'Latency'].map((header) => <th key={header} className="text-left text-xs text-slate-500 uppercase tracking-wide font-medium py-3 border-b border-slate-200">{header}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const tone = row.model?.includes('claude') ? 'bg-blue-50' : row.model?.includes('gemini') ? 'bg-purple-50' : 'bg-slate-50';
            return (
              <Fragment key={row.id || index}>
                <tr key={row.id || index} className={`${tone} cursor-pointer`} onClick={() => setOpen(open === index ? null : index)}>
                  <td className="font-mono text-xs text-slate-500 py-3">{row.timestamp}</td>
                  <td className="text-sm text-slate-700 font-medium py-3">{row.agent_name}</td>
                  <td className="text-sm text-slate-600 font-mono py-3">{row.tool_name || row.action}</td>
                  <td className="py-3"><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${row.model?.includes('claude') ? 'bg-blue-100 text-blue-700' : row.model?.includes('gemini') ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-700'}`}>{row.model || 'deterministic'}</span></td>
                  <td className={`font-mono text-xs py-3 ${(row.latency_ms || 0) > 3000 ? 'text-red-600' : (row.latency_ms || 0) > 1000 ? 'text-amber-600' : 'text-emerald-600'}`}>{row.latency_ms || 0}ms</td>
                </tr>
                {open === index && (
                  <tr>
                    <td colSpan="5" className="glass-subcard p-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap">{JSON.stringify({ input: row.tool_input, output: row.tool_output, response: row.response }, null, 2)}</td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
