import { Target } from 'lucide-react';

export default function WeeklyChallenge({ name, description, current, target }) {
  const pct = target ? (current / target) * 100 : 0;
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 font-medium text-slate-700"><Target className="text-amber-500" size={18} /> {name}</div>
      <div className="text-sm text-slate-500 mt-2">{description}</div>
      <div className="h-3 bg-slate-100/90 rounded-full mt-4 overflow-hidden">
        <div className="h-3 rounded-full bg-gradient-to-r from-amber-400 to-emerald-500" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <div className="text-sm text-slate-600 mt-3">{current}/{target} days</div>
    </div>
  );
}
