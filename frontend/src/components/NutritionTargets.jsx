export default function NutritionTargets({ data, title = 'Daily Nutrition Targets', subtitle }) {
  if (!data) {
    return <div className="glass-card p-6 text-sm text-slate-500">Nutrition targets unavailable.</div>;
  }
  const cards = [
    ['Calories', data.current_calories || 0, data.calories || 0],
    ['Protein', data.current_protein_g || 0, data.protein_g || 0],
    ['Carbs', data.current_carbs_g || 0, data.carbs_g || 0],
    ['Fat', data.current_fat_g || 0, data.fat_g || 0],
    ['Sat Fat', data.current_sat_fat_g || 0, data.sat_fat_g || 0]
  ];

  return (
    <div className="space-y-4">
      <div>
        <div className="text-lg font-semibold text-slate-900">{title}</div>
        <p className="mt-1 text-sm text-slate-500">{subtitle || data.reasoning?.[0] || 'Targets are tuned to your current blood work and body composition.'}</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map(([label, current, target]) => {
          const pct = target ? Math.round((current / target) * 100) : 0;
          const color = pct > 100 ? 'bg-red-500' : pct >= 80 ? 'bg-emerald-400' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
          return (
            <div key={label} className="glass-card p-4 text-center">
              <div className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</div>
              <div className="text-lg font-mono font-medium tabular-nums text-slate-900 mt-2">{current}/{target}</div>
              <div className="h-2 bg-slate-100 rounded-full mt-2">
                <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
              </div>
              <div className="text-xs text-slate-500 mt-1">{pct}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
