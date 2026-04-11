import { Activity, Dumbbell, Heart, PersonStanding } from 'lucide-react';

const icons = {
  running: PersonStanding,
  walking: Activity,
  cycling: Activity,
  swimming: Activity,
  yoga: Heart,
  strength_training: Dumbbell,
  weight_training: Dumbbell
};

const sourceLabels = {
  manual: 'Logged on',
  healthkit_mobile: 'Synced on',
  apple_health: 'Synced on',
  mobile: 'Synced on'
};

function formatDateTime(value) {
  if (!value) return null;
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? `${value}T12:00:00`
    : /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
      ? value.replace(' ', 'T')
      : value;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: /^\d{4}-\d{2}-\d{2}$/.test(value) ? undefined : 'short' });
}

function formatDayLabel(value) {
  if (!value) return 'Unknown day';
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value.replace(' ', 'T');
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
}

function groupWorkoutsByDay(workouts) {
  const grouped = new Map();
  workouts.forEach((workout) => {
    const key = String(workout.date || workout.timestamp || '').slice(0, 10) || 'unknown';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(workout);
  });
  return Array.from(grouped.entries()).map(([day, dayWorkouts]) => ({ day, dayWorkouts }));
}

export default function WorkoutLog({ workouts = [] }) {
  const groupedWorkouts = groupWorkoutsByDay(workouts);

  return (
    <div className="glass-card p-6">
      {groupedWorkouts.length ? groupedWorkouts.map(({ day, dayWorkouts }) => (
        <div key={day} className="mb-5 last:mb-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{formatDayLabel(day)}</div>
          <div className="space-y-3">
            {dayWorkouts.map((workout) => {
              const Icon = icons[workout.type] || Activity;
              const impact = [workout.cv_impact, workout.msk_impact, workout.met_impact, workout.neuro_impact].filter(Boolean)[0];
              const eventTime = formatDateTime(workout.timestamp || workout.date);
              const sourceLabel = sourceLabels[String(workout.source || 'manual').toLowerCase()] || 'Logged on';
              return (
                <div key={workout.id} className="glass-subcard px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Icon size={18} className="text-slate-500" />
                      <span className="font-medium text-slate-700 capitalize">{String(workout.type || '').replaceAll('_', ' ')}</span>
                    </div>
                    <div className="text-sm text-slate-500">{workout.duration_min} min · {workout.calories || 0} cal</div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>{sourceLabel} {eventTime || workout.date}</span>
                    <span>Source: {String(workout.source || 'manual').replaceAll('_', ' ')}</span>
                  </div>
                  <div className="text-xs text-emerald-600 mt-2">Impact: {impact ? `${impact} years` : 'steady maintenance'}</div>
                </div>
              );
            })}
          </div>
        </div>
      )) : <div className="empty-state-card px-4 py-5 text-sm text-slate-500">No workouts logged yet. Add your first session above and your activity timeline will start filling in here.</div>}
    </div>
  );
}
