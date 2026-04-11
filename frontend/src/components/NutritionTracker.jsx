import { Droplets } from 'lucide-react';
import { useState } from 'react';
import { logWater } from '../api';
import useStore from '../store';

export default function NutritionTracker({ target, currentOverride, readOnly = false, dayLabel = 'today' }) {
  const { selectedUserId, dashboard, showToast, setDashboard } = useStore();
  const [custom, setCustom] = useState('');
  const current = currentOverride ?? dashboard?.water_today_ml ?? 0;
  const goal = target ?? dashboard?.nutrition_targets?.water_ml ?? 2450;
  const pct = Math.min((current / goal) * 100, 100);

  const addWater = async (amount) => {
    try {
      const response = await logWater(selectedUserId, amount);
      setDashboard({ ...dashboard, water_today_ml: response.data.today_total_ml });
      showToast('Water logged');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 font-medium text-slate-700"><Droplets className="text-blue-500" size={20} /> Water Tracker</div>
      <div className="text-2xl font-mono font-medium text-slate-900 mt-4">{current.toLocaleString()}ml <span className="text-sm text-slate-500">/ {goal.toLocaleString()}ml</span></div>
      <div className="h-3 bg-slate-100 rounded-full mt-4">
        <div className="h-3 bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      {readOnly ? (
        <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Viewing {dayLabel}. Water logging is disabled while you are previewing another day.
        </div>
      ) : null}
      <div className="flex gap-2 mt-3 flex-wrap">
        <button disabled={readOnly} onClick={() => addWater(250)} className="border border-slate-300 text-slate-700 rounded-lg px-4 py-2 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">+250ml</button>
        <button disabled={readOnly} onClick={() => addWater(500)} className="border border-slate-300 text-slate-700 rounded-lg px-4 py-2 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">+500ml</button>
        <div className="flex gap-2">
          <input disabled={readOnly} value={custom} onChange={(event) => setCustom(event.target.value)} placeholder="Custom" className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-24 disabled:cursor-not-allowed disabled:bg-slate-100" />
          <button disabled={readOnly} onClick={() => { if (custom) addWater(Number(custom)); setCustom(''); }} className="border border-slate-300 text-slate-700 rounded-lg px-4 py-2 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">Add</button>
        </div>
      </div>
    </div>
  );
}
