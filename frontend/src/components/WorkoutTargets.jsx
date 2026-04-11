import { Dumbbell, Heart, PersonStanding } from 'lucide-react';

const icons = { running: PersonStanding, yoga: Heart, strength: Dumbbell, walking: PersonStanding, cycling: PersonStanding, weight_training: Dumbbell, hiit: Dumbbell };

export default function WorkoutTargets({ data }) {
  const sessions = data?.recommended_sessions || [];
  const priorities = data?.priority_areas || [];
  const trackingWindowDays = data?.tracking_window_days || 7;
  return (
    <div className="glass-card p-6">
      <div className="mb-4">
        <div className="text-lg font-semibold text-slate-900">Recommended for your current profile</div>
        <div className="text-sm text-slate-600 mt-1">
          {priorities.length
            ? `These recommendations are being generated from your current weak points: ${priorities.join(', ')}.`
            : 'These recommendations are being generated from your current profile and weekly activity context.'}
        </div>
        <div className="text-xs text-slate-500 mt-2">
          Progress updates automatically from workouts you log in the last {trackingWindowDays} days.
        </div>
      </div>
      {sessions.length ? sessions.map((session, index) => {
        const Icon = icons[session.type] || PersonStanding;
        const targetSessions = session.target_sessions || 0;
        const completedSessions = session.completed_sessions || 0;
        const completionPercent = Math.min(Math.round((session.completion_ratio || 0) * 100), 100);
        const statusClass = session.status === 'complete'
          ? 'bg-emerald-500'
          : session.status === 'in_progress'
            ? 'bg-amber-500'
            : 'bg-slate-300';
        return (
          <div key={`${session.type}-${index}`} className={`glass-subcard ${index < sessions.length - 1 ? 'mb-3' : ''} px-4 py-4`}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Icon size={18} className="text-slate-500" />
                <div className="font-medium text-slate-700">{session.type}</div>
                <div className="text-sm text-slate-500">{session.frequency}</div>
              </div>
              <div className={`text-xs font-semibold uppercase tracking-wide ${
                session.status === 'complete' ? 'text-emerald-700' : session.status === 'in_progress' ? 'text-amber-700' : 'text-slate-500'
              }`}>
                {session.status === 'complete' ? 'done' : session.status === 'in_progress' ? 'in progress' : 'not started'}
              </div>
            </div>
            <div className="text-xs text-slate-500 mt-2">{session.reason}</div>
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
                <span>{completedSessions}/{targetSessions} sessions logged</span>
                <span>{completionPercent}% complete</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div className={`h-2 rounded-full transition-all ${statusClass}`} style={{ width: `${completionPercent}%` }} />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500 mt-2">
                <span>{session.completed_minutes || 0}/{session.target_minutes || 0} min</span>
                <span>
                  {session.remaining_sessions > 0
                    ? `${session.remaining_sessions} session${session.remaining_sessions === 1 ? '' : 's'} to go`
                    : 'Target hit'}
                </span>
              </div>
              {!!session.last_logged_at && (
                <div className="text-[11px] text-slate-400 mt-1">
                  Last matching workout: {session.last_logged_at}
                </div>
              )}
            </div>
          </div>
        );
      }) : <div className="empty-state-card px-4 py-5 text-sm text-slate-500">No workout targets available yet. As soon as enough activity data is present, recommendations will populate here.</div>}
    </div>
  );
}
