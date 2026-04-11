export default function AchievementGrid({ achievements = [] }) {
  const defs = [
    { id: 'first_blood', name: 'First Blood', icon_emoji: '🩸' },
    { id: 'face_future', name: 'Face Future', icon_emoji: '📸' },
    { id: 'stand_tall', name: 'Stand Tall', icon_emoji: '🧍' },
    { id: 'week_warrior', name: 'Week Warrior', icon_emoji: '🔥' },
    { id: 'data_complete', name: 'Data Complete', icon_emoji: '📊' }
  ];
  return (
    <div className="glass-card glass-card-hover p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-lg font-semibold text-slate-900">Achievements</div>
          <div className="text-sm text-slate-600">Unlocked badges glow. Locked badges stay muted until you earn them.</div>
        </div>
        <div className="text-sm text-slate-500">Earned: {achievements.length}/{defs.length}</div>
      </div>
      {!achievements.length ? (
        <div className="empty-state-card mt-5 px-4 py-4 text-sm text-slate-600">
          No achievements unlocked yet. Log a meal, keep a streak alive, or complete your first future-self check-in to wake these up.
        </div>
      ) : null}
      <div className="grid grid-cols-5 gap-4">
        {defs.map((item) => {
          const earned = achievements.some((achievement) => achievement.badge_id === item.id);
          return (
            <div key={item.id} className="text-center">
              <div className={`mt-5 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto text-2xl ${earned ? 'bg-emerald-50 border border-emerald-200 pulse-glow' : 'bg-slate-50 border border-slate-200 opacity-50 grayscale'}`}>{item.icon_emoji}</div>
              <div className={`text-xs mt-1 font-medium ${earned ? 'text-slate-700' : 'text-slate-400'}`}>{item.name}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
