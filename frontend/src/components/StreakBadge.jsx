import { Flame } from 'lucide-react';
import useStore from '../store';

export default function StreakBadge() {
  const { gamification } = useStore();
  const streak = gamification?.current_streak || 0;

  return (
    <div title={`${streak}-day streak! Complete 3 health actions today to keep it going.`} className="flex items-center gap-2">
      <Flame size={18} className={streak > 0 ? 'text-orange-500' : 'text-slate-300'} />
      <span className={streak > 0 ? 'text-sm font-semibold text-orange-600' : 'text-slate-400 text-sm'}>{streak}</span>
    </div>
  );
}
