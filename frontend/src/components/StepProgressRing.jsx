export default function StepProgressRing({ current = 0, goal = 7500, size = 160, compact = false, note = null }) {
  const strokeWidth = 8;
  const radius = (size - 16) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(current / Math.max(goal, 1), 1);
  const dashoffset = circumference - circumference * pct;
  const color = pct > 0.7 ? '#10b981' : pct >= 0.4 ? '#f59e0b' : '#ef4444';
  return (
    <div className={`glass-card ${compact ? 'p-4' : 'p-6'} flex flex-col items-center`}>
      <svg viewBox={`0 0 ${size} ${size}`} className={`w-full ${compact ? 'max-w-[160px]' : 'max-w-[220px]'}`}>
        <circle cx={center} cy={center} r={radius} stroke="#e2e8f0" strokeWidth={strokeWidth} fill="none" />
        <circle cx={center} cy={center} r={radius} stroke={color} strokeWidth={strokeWidth} fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashoffset} transform={`rotate(-90 ${center} ${center})`} style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
        <text x={center} y={center} textAnchor="middle" className={`fill-slate-900 ${compact ? 'text-[16px]' : 'text-[20px]'} font-mono font-medium`}>{current.toLocaleString()}</text>
        <text x={center} y={center + 18} textAnchor="middle" className="fill-slate-400 text-[12px]">/ {goal.toLocaleString()}</text>
      </svg>
      <div className={`${compact ? 'text-xs mt-2' : 'text-sm mt-3'} text-slate-500 text-center`}>steps today{note ? ' (estimated + tracked)' : ''}</div>
      {note ? <div className="mt-2 text-[11px] text-slate-400 text-center">{note}</div> : null}
    </div>
  );
}
