import { BrainCircuit, CloudSun, Footprints } from 'lucide-react';

export default function ActivityNudge({ currentSteps, stepGoal, nudge, compact = false }) {
  if (!nudge && currentSteps >= stepGoal) return null;
  const title = nudge?.title || 'Daily movement nudge';
  const message = nudge?.message || `You're ${(stepGoal - currentSteps).toLocaleString()} steps behind your goal. A 20-minute walk would get you there!`;
  const conditions = nudge?.conditions;
  const Icon = nudge?.type === 'fresh_air_reset' ? BrainCircuit : Footprints;
  const accentClass = conditions?.outdoor_ok ? 'border-emerald-500 bg-emerald-50' : 'border-amber-500 bg-amber-50';

  return (
    <div className={`border-l-4 rounded-r-lg ${accentClass} ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-start gap-3">
        <Icon className={conditions?.outdoor_ok ? 'text-emerald-600' : 'text-amber-600'} size={compact ? 18 : 20} />
        <div className="min-w-0">
          <div className={`font-semibold ${compact ? 'text-xs' : 'text-sm'} text-slate-900`}>{title}</div>
          <div className={`${compact ? 'text-xs' : 'text-sm'} text-slate-700 mt-1`}>{message}</div>
          {nudge?.suggested_activity && (
            <div className="mt-2 text-xs font-medium text-emerald-700">
              Suggested next move: {nudge.suggested_activity}
            </div>
          )}
          {conditions?.summary && (
            <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-[11px] text-slate-600">
              <CloudSun size={12} />
              {conditions.summary}
            </div>
          )}
          {conditions?.note && (
            <div className="mt-2 text-[11px] text-slate-500">{conditions.note}</div>
          )}
        </div>
      </div>
    </div>
  );
}
