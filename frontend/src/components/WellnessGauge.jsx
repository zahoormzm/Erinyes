import FormulaTooltip from './FormulaTooltip';

export default function WellnessGauge({ score = 0, breakdown = [], userId = null }) {
  const clamped = Math.max(0, Math.min(score, 100));
  const circumference = 2 * Math.PI * 80;
  const progress = circumference - (clamped / 100) * circumference;
  const color = clamped <= 30 ? '#ef4444' : clamped <= 60 ? '#f59e0b' : '#10b981';

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm hover:shadow-md transition-shadow p-6">
      <svg viewBox="0 0 200 160" className="w-full max-w-[260px] mx-auto">
        <path d="M43.43 156.57 A80 80 0 1 1 156.57 156.57" fill="none" stroke="#e2e8f0" strokeWidth="12" />
        <path
          d="M43.43 156.57 A80 80 0 1 1 156.57 156.57"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={progress}
        />
        <text x="100" y="88" textAnchor="middle" className="fill-slate-900 text-3xl font-bold">{clamped}</text>
        <text x="100" y="110" textAnchor="middle" className="fill-slate-500 text-sm">Mental Wellness</text>
      </svg>
      {userId ? (
        <div className="mt-2 flex justify-center">
          <FormulaTooltip userId={userId} metric="mental_wellness_score">
            <div className="text-sm font-medium text-slate-700">Formula breakdown</div>
          </FormulaTooltip>
        </div>
      ) : null}
      <div className="mt-6">
        {breakdown.length ? breakdown.map((item) => (
          <div key={item.name} className="flex justify-between py-1.5 border-b border-slate-100">
            <span className="text-sm text-slate-600">{item.name}</span>
            <FormulaTooltip userId={userId} metric={`${String(item.name).toLowerCase().replaceAll(' ', '_')}_penalty`}>
              <span className="text-sm text-red-500">-{item.penalty}</span>
            </FormulaTooltip>
          </div>
        )) : <div className="text-sm text-slate-500">Complete a mental health check-in to see your wellness score.</div>}
      </div>
    </div>
  );
}
