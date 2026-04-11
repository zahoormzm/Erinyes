export default function XPBar({ level = 1, levelName = 'Health Rookie', currentXP = 0, nextLevelXP = 100 }) {
  const width = Math.min((currentXP / Math.max(nextLevelXP, 1)) * 100, 100);
  return (
    <div className="glass-card p-6">
      <div className="text-2xl font-bold text-slate-900">Level {level}</div>
      <div className="text-sm text-slate-500">{levelName}</div>
      <div className="h-4 bg-slate-100/90 rounded-full mt-4 overflow-hidden">
        <div className="h-4 rounded-full bg-gradient-to-r from-emerald-400 to-sky-500 transition-all" style={{ width: `${width}%` }} />
      </div>
      <div className="text-xs text-slate-500 mt-2">{currentXP} / {nextLevelXP} XP</div>
    </div>
  );
}
