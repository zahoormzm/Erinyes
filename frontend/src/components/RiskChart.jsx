import { useState } from 'react';
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const METRICS = [
  { key: 'diabetes_risk', label: 'Diabetes', color: '#2563eb', accent: 'bg-blue-50 border-blue-200 text-blue-800', description: 'Glucose and metabolic strain over time.' },
  { key: 'cvd_risk', label: 'Heart', color: '#dc2626', accent: 'bg-red-50 border-red-200 text-red-800', description: 'Cardiovascular load and blood-vessel risk.' },
  { key: 'metabolic_risk', label: 'Metabolic', color: '#d97706', accent: 'bg-amber-50 border-amber-200 text-amber-800', description: 'Weight, lipids, and long-run metabolic pressure.' },
  { key: 'mental_decline_risk', label: 'Cognitive', color: '#7c3aed', accent: 'bg-violet-50 border-violet-200 text-violet-800', description: 'Mental resilience and long-term decline risk.' }
];

const SNAPSHOT_YEARS = [5, 10, 15];

function percent(value) {
  return ((value || 0) * 100);
}

function snapshotForYear(rows, year) {
  return rows.find((row) => Number(row?.year) === year) || rows[rows.length - 1] || null;
}

function buildChartRows(data, comparisonData, metricKey) {
  const comparisonByYear = new Map((comparisonData || []).map((row) => [Number(row.year), row]));
  return (data || []).map((row) => {
    const comparison = comparisonByYear.get(Number(row.year));
    return {
      year: Number(row.year),
      current: percent(row[metricKey]),
      scenario: comparison ? percent(comparison[metricKey]) : null
    };
  });
}

function topDomain(rows) {
  const values = rows.flatMap((row) => [row.current, row.scenario].filter((value) => value !== null && value !== undefined));
  const maxValue = Math.max(10, ...values, 0);
  return Math.min(100, Math.ceil(maxValue / 5) * 5 + 5);
}

function deltaText(delta) {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return 'No scenario';
  if (Math.abs(delta) < 0.05) return 'No material change';
  if (delta < 0) return `${Math.abs(delta).toFixed(1)} pts lower`;
  return `${delta.toFixed(1)} pts higher`;
}

function deltaClass(delta) {
  if (delta === null || delta === undefined || Number.isNaN(delta) || Math.abs(delta) < 0.05) return 'text-slate-600';
  return delta < 0 ? 'text-emerald-700' : 'text-red-700';
}

export default function RiskChart({
  data = [],
  comparisonData = [],
  title = 'Risk Forecast',
  subtitle = 'Lower lines are better. Farther right means farther into the future.',
  nextStepText = '',
  checkpointText = '',
  readHint = ''
}) {
  const [selectedMetric, setSelectedMetric] = useState(METRICS[0].key);

  if (!data.length) {
    return <div className="glass-card p-6 text-sm text-slate-500">No risk projection data yet.</div>;
  }

  const metric = METRICS.find((item) => item.key === selectedMetric) || METRICS[0];
  const rows = buildChartRows(data, comparisonData, metric.key);
  const domainMax = topDomain(rows);
  const hasScenario = Boolean(comparisonData?.length);

  return (
    <div className="glass-card p-6 space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-lg font-semibold text-slate-900">{title}</div>
          <div className="text-sm text-slate-600 mt-1">{subtitle}</div>
        </div>
        <div className="text-xs text-slate-500">
          Solid area = current saved profile
          {hasScenario ? ' | dashed line = last simulation' : ''}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {METRICS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setSelectedMetric(item.key)}
            className={`rounded-full border px-3 py-1.5 text-sm transition ${
              selectedMetric === item.key ? item.accent : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className={`rounded-xl border p-4 ${metric.accent}`}>
        <div className="text-sm font-semibold">{metric.label} risk</div>
        <div className="text-sm opacity-90 mt-1">{metric.description}</div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {SNAPSHOT_YEARS.map((year) => {
          const currentRow = snapshotForYear(data, year);
          const scenarioRow = snapshotForYear(comparisonData, year);
          const current = currentRow ? percent(currentRow[metric.key]) : null;
          const scenario = scenarioRow ? percent(scenarioRow[metric.key]) : null;
          const delta = scenario !== null && current !== null ? scenario - current : null;
          return (
            <div key={year} className="glass-subcard p-4">
              <div className="text-xs uppercase tracking-wide font-semibold text-slate-500">Year {year}</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">
                {current !== null ? `${current.toFixed(1)}%` : 'N/A'}
              </div>
              <div className="text-sm text-slate-600 mt-1">Current forecast</div>
              {hasScenario && (
                <>
                  <div className="mt-3 text-lg font-semibold text-slate-900">
                    {scenario !== null ? `${scenario.toFixed(1)}%` : 'N/A'}
                  </div>
                  <div className="text-sm text-slate-600 mt-1">Scenario forecast</div>
                  <div className={`text-sm font-medium mt-3 ${deltaClass(delta)}`}>{deltaText(delta)}</div>
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
            <defs>
              <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={metric.color} stopOpacity={0.28} />
                <stop offset="95%" stopColor={metric.color} stopOpacity={0.04} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="year" tickLine={false} axisLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
            <YAxis
              domain={[0, domainMax]}
              tickFormatter={(value) => `${value}%`}
              tickLine={false}
              axisLine={false}
              tick={{ fill: '#64748b', fontSize: 12 }}
            />
            <Tooltip
              formatter={(value) => `${Number(value).toFixed(1)}%`}
              contentStyle={{ borderRadius: 14, borderColor: '#cbd5e1', boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)' }}
              labelFormatter={(label) => `Year ${label}`}
            />
            <ReferenceLine y={10} stroke="#cbd5e1" strokeDasharray="4 4" />
            <Area type="monotone" dataKey="current" stroke={metric.color} strokeWidth={3} fill="url(#riskFill)" />
            {hasScenario && (
              <Area
                type="monotone"
                dataKey="scenario"
                stroke={metric.color}
                strokeWidth={3}
                strokeDasharray="7 7"
                fillOpacity={0}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="glass-subcard p-4">
          <div className="text-xs uppercase tracking-wide font-semibold text-slate-500">How to read it</div>
          <div className="text-sm text-slate-600 mt-2">{readHint || 'Higher curves mean higher cumulative risk over time. A lower dashed scenario line means the simulated habit change improves outlook.'}</div>
        </div>
        <div className="glass-subcard p-4">
          <div className="text-xs uppercase tracking-wide font-semibold text-slate-500">Most useful checkpoint</div>
          <div className="text-sm text-slate-600 mt-2">{checkpointText || 'Year 10 is usually the clearest summary. It is far enough out to show trend, but not so far out that everything looks inflated.'}</div>
        </div>
        <div className="glass-subcard p-4">
          <div className="text-xs uppercase tracking-wide font-semibold text-slate-500">What to do next</div>
          <div className="text-sm text-slate-600 mt-2">{nextStepText || 'Try one slider change at a time, then check whether the dashed line drops. That tells you which habit has the strongest leverage.'}</div>
        </div>
      </div>
    </div>
  );
}
