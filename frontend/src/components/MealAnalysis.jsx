import { AlertTriangle, CheckCircle } from 'lucide-react';

export default function MealAnalysis({ analysis }) {
  if (!analysis) {
    return <div className="glass-card p-6 text-sm text-slate-500">Upload or analyze a meal to see results.</div>;
  }
  const total = analysis.total || {};
  return (
    <div className="glass-card p-6">
      <table className="w-full text-left">
        <thead>
          <tr className="text-xs text-slate-500 uppercase tracking-wide font-medium">
            <th className="pb-3">Item</th>
            <th className="pb-3">Portion</th>
            <th className="pb-3">Calories</th>
            <th className="pb-3">Protein</th>
            <th className="pb-3">Sat Fat</th>
          </tr>
        </thead>
        <tbody>
          {(analysis.items || []).map((item, index) => (
            <tr key={`${item.item}-${index}`} className="border-b border-slate-100">
              <td className="py-3 font-mono text-sm">
                {item.item}
                <div className="text-xs text-slate-400 pl-4">{item.usda_id ? `USDA #${item.usda_id}` : item.usda_description}</div>
              </td>
              <td className="py-3 font-mono text-sm">{item.portion_g}g</td>
              <td className="py-3 font-mono text-sm">{item.calories}</td>
              <td className="py-3 font-mono text-sm">{item.protein_g}</td>
              <td className="py-3 font-mono text-sm">{item.sat_fat_g}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-300 font-bold">
            <td className="pt-3">TOTAL</td>
            <td />
            <td className="pt-3 font-mono">{total.calories}</td>
            <td className="pt-3 font-mono">{total.protein_g}</td>
            <td className="pt-3 font-mono">{total.sat_fat_g}</td>
          </tr>
        </tbody>
      </table>
      <div className="mt-4 space-y-2">
        {(analysis.flags || []).map((flag, index) => (
          <div key={index} className="flex items-center gap-2 text-amber-700 text-sm"><AlertTriangle size={16} /> {flag}</div>
        ))}
        {!analysis.flags?.length && <div className="flex items-center gap-2 text-emerald-700 text-sm"><CheckCircle size={16} /> Meal is within your current targets.</div>}
        <div className="text-lg font-semibold mt-3">Score: {(analysis.health_score || analysis.score || 7.2)}/10</div>
        <div className="text-sm text-slate-500 mt-2">
          This meal analysis is now available to the Nutrition Coach below, so you can ask AI about this exact upload.
        </div>
      </div>
    </div>
  );
}
