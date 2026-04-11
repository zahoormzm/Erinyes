import { ArrowDown, ArrowUp } from 'lucide-react';

const STATUS_LABELS = {
  good: 'On track',
  warning: 'Needs attention',
  critical: 'Take action',
  neutral: '—',
};

export default function MetricCard({ label, value, unit, delta, icon: Icon, status = 'neutral', compact = false, hint = '' }) {
  const statusClass = {
    good: 'border-l-emerald-400',
    warning: 'border-l-amber-400',
    critical: 'border-l-red-400',
    neutral: 'border-l-slate-300'
  }[status];
  const statusTextClass = {
    good: 'text-emerald-600',
    warning: 'text-amber-600',
    critical: 'text-red-600',
    neutral: 'text-slate-400',
  }[status];
  const display = value == null ? '—' : Number.isInteger(value) ? value.toLocaleString() : Number(value).toFixed(1);

  return (
    <div className={`bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 border-l-4 ${statusClass} shadow-sm hover:shadow-md transition-shadow ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-center justify-between">
        <Icon size={compact ? 18 : 20} className="text-slate-400" />
        <span className={`text-[11px] font-medium tracking-wide ${statusTextClass}`}>{STATUS_LABELS[status] || status}</span>
      </div>
      <div className={`${compact ? 'text-xs mt-2' : 'text-sm mt-3'} font-semibold uppercase tracking-wider text-slate-500`}>{label}</div>
      <div className={`${compact ? 'text-xl' : 'text-2xl'} font-bold tabular-nums text-slate-900 mt-1 transition-all duration-300`}>{display}</div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-slate-400">{unit}</span>
        {delta != null && (
          <span className={`text-xs font-medium flex items-center gap-1 ${delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {delta >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
            {Math.abs(delta).toFixed(1)}
          </span>
        )}
      </div>
      {hint ? <div className="text-[11px] text-slate-400 mt-1.5 leading-snug">{hint}</div> : null}
    </div>
  );
}
