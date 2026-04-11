import { Activity, BrainCircuit, CloudSun, Droplets, Footprints, HeartPulse, MonitorOff, Moon, Music2, PersonStanding, Pill, RefreshCw, Utensils, Wind } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getSmartReminders, logWater } from '../api';
import useStore from '../store';

const iconMap = {
  droplets: Droplets,
  footprints: Footprints,
  activity: Activity,
  sun: CloudSun,
  pill: Pill,
  moon: Moon,
  'heart-pulse': HeartPulse,
  wind: Wind,
  'monitor-off': MonitorOff,
  utensils: Utensils,
  'person-standing': PersonStanding,
  'cloud-sun': CloudSun,
  music: Music2,
  fresh_air_reset: BrainCircuit,
  step_nudge: Footprints,
  exercise_nudge: Activity,
};

const priorityClass = {
  high: 'border-l-red-500 bg-red-50/80',
  medium: 'border-l-amber-500 bg-amber-50/80',
  low: 'border-l-blue-500 bg-blue-50/80',
};

function ActionLabel({ action }) {
  return {
    log_water: 'Log Water',
    open_activity: 'Open Activity',
    open_nutrition: 'Open Nutrition',
    open_mental: 'Open Mental',
    open_posture: 'Open Posture',
  }[action] || 'Open';
}

export default function ReminderCards() {
  const navigate = useNavigate();
  const { reminders, selectedUserId, setDashboard, setReminders, showToast } = useStore();
  const [loading, setLoading] = useState(false);
  const [waterModal, setWaterModal] = useState(false);
  const [customWater, setCustomWater] = useState('300');

  const refresh = async () => {
    if (!selectedUserId) return;
    setLoading(true);
    try {
      const response = await getSmartReminders(selectedUserId);
      setReminders(response.data || []);
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [selectedUserId]);

  const reloadDashboard = async () => {
    try {
      const response = await getDashboard(selectedUserId);
      setDashboard(response.data);
    } catch {
      // no-op
    }
  };

  const handleAction = async (action) => {
    if (action === 'log_water') {
      setWaterModal(true);
      return;
    }
    if (action === 'open_activity') navigate('/activity');
    if (action === 'open_nutrition') navigate('/nutrition');
    if (action === 'open_mental') navigate('/mental');
    if (action === 'open_posture') navigate('/posture');
  };

  const quickLogWater = async (amount) => {
    try {
      await logWater(selectedUserId, amount);
      setWaterModal(false);
      await Promise.all([refresh(), reloadDashboard()]);
      showToast('Water logged');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  if (!reminders?.length) {
    return (
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">Smart Reminders</div>
            <div className="text-sm text-slate-500 mt-2">No nudges right now. Your current context looks stable.</div>
          </div>
          <button type="button" onClick={refresh} className="rounded-full border border-slate-200 p-2 text-slate-500 hover:text-slate-700 transition">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="min-w-0">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">Smart Reminders</div>
            <div className="text-sm text-slate-500 mt-1">Context-aware nudges based on hydration, recovery, movement, weather, meals, and mood.</div>
          </div>
          <button type="button" onClick={refresh} className="rounded-full border border-slate-200 bg-white p-2 text-slate-500 hover:text-slate-700 transition">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
        <div className="flex gap-4 overflow-x-auto pb-2 pr-1 snap-x snap-mandatory">
          {reminders.map((reminder, index) => {
            const Icon = iconMap[reminder.icon] || Activity;
            return (
              <div key={`${reminder.type}-${index}`} className={`snap-start flex-shrink-0 w-[22rem] max-w-[85vw] rounded-2xl border border-slate-200/60 border-l-4 p-4 shadow-sm ${priorityClass[reminder.priority] || priorityClass.low}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                    <Icon size={16} className="text-slate-600" />
                    <span className="capitalize">{reminder.title || String(reminder.type).replaceAll('_', ' ')}</span>
                  </div>
                  <span className="text-[11px] uppercase tracking-wide text-slate-500">{reminder.priority}</span>
                </div>
                <div className="mt-3 text-sm text-slate-700 leading-relaxed">{reminder.message}</div>
                {reminder.suggested_activity ? (
                  <div className="mt-3 text-xs font-medium text-emerald-700">
                    Suggested next move: {reminder.suggested_activity}
                  </div>
                ) : null}
                {reminder.conditions?.summary ? (
                  <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-[11px] text-slate-600">
                    <CloudSun size={12} />
                    {reminder.conditions.summary}
                  </div>
                ) : null}
                {reminder.conditions?.note ? (
                  <div className="mt-2 text-[11px] text-slate-500">{reminder.conditions.note}</div>
                ) : null}
                {reminder.action ? (
                  <button
                    type="button"
                    onClick={() => handleAction(reminder.action)}
                    className="mt-4 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-emerald-300 hover:text-emerald-700 transition"
                  >
                    <ActionLabel action={reminder.action} />
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
      {waterModal ? (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="glass-card p-6 max-w-sm w-full shadow-2xl">
            <div className="text-lg font-bold text-slate-900">Quick Water Log</div>
            <div className="text-sm text-slate-500 mt-2">Add hydration without leaving the dashboard.</div>
            <div className="grid grid-cols-3 gap-2 mt-4">
              {[250, 500, 750].map((amount) => (
                <button key={amount} type="button" onClick={() => quickLogWater(amount)} className="glass-subcard px-3 py-2 text-sm hover:border-emerald-300 hover:text-emerald-700 transition">
                  {amount}ml
                </button>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <input value={customWater} onChange={(event) => setCustomWater(event.target.value)} className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm" />
              <button type="button" onClick={() => quickLogWater(Number(customWater) || 250)} className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 transition">
                Log
              </button>
            </div>
            <button type="button" onClick={() => setWaterModal(false)} className="mt-4 text-sm text-slate-500 hover:text-slate-700 transition">
              Close
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
