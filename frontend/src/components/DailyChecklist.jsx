import { CheckCircle, Circle } from 'lucide-react';
import { logAction } from '../api';
import useStore from '../store';

export default function DailyChecklist({ data }) {
  const { selectedUserId, showToast, setGamification, gamification } = useStore();
  const checklist = data || [
    { action: 'meal_log', xp: 10, completed: gamification?.today_actions?.includes('meal_log') },
    { action: 'water_goal', xp: 5, completed: gamification?.today_actions?.includes('water_goal') },
    { action: 'exercise_goal', xp: 15, completed: gamification?.today_actions?.includes('exercise_goal') }
  ];

  const complete = async (action) => {
    try {
      const response = await logAction(selectedUserId, action);
      setGamification(response.data);
      showToast('Action logged');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  return (
    <div className="glass-card p-6">
      <h3 className="font-semibold text-slate-900 mb-4">Today's Health Actions</h3>
      {checklist.length ? checklist.map((item) => (
        <button key={item.action} onClick={() => !item.completed && complete(item.action)} className="w-full flex items-center gap-3 py-2.5 border-b border-slate-100 text-left">
          {item.completed ? <CheckCircle className="text-emerald-500" size={18} /> : <Circle className="text-slate-300" size={18} />}
          <span className={`text-sm ${item.completed ? 'line-through text-slate-400' : 'text-slate-700'}`}>{item.action.replace('_', ' ')}</span>
          <span className="ml-auto text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">+{item.xp} XP</span>
        </button>
      )) : (
        <div className="empty-state-card px-4 py-4 text-sm text-slate-600">
          No actions are queued for today yet. Once the profile has reminders and daily goals, they will appear here.
        </div>
      )}
      <div className="text-xs text-slate-500 mt-2">Complete 3 actions for streak day</div>
    </div>
  );
}
