import { Bell, Menu } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import useStore from '../store';
import StreakBadge from './StreakBadge';
import UserSelector from './UserSelector';

const titles = {
  '/': 'Dashboard',
  '/ingest': 'Data Ingest',
  '/insights': 'Insights',
  '/research': 'Research Lab',
  '/mental': 'Mental Health',
  '/nutrition': 'Nutrition',
  '/future': 'Future Self',
  '/activity': 'Activity',
  '/posture': 'Posture',
  '/gamification': 'Gamification',
  '/family': 'Family',
  '/settings': 'Settings'
};

export default function TopBar({ onMenu = () => {} }) {
  const location = useLocation();
  const { alerts, profile, selectedUserId } = useStore();

  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200/60 px-4 md:px-6 py-3 flex justify-between items-center sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onMenu} className="glass-subcard md:hidden p-2 text-slate-600 hover:text-slate-900 transition">
          <Menu size={18} />
        </button>
        <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{titles[location.pathname] || 'EirView'}</h1>
        <p className="text-sm text-slate-500">
          EirView. Your progress, in full focus.
          <span className="ml-2 text-slate-400">Viewing {profile?.name || selectedUserId}</span>
        </p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <UserSelector />
        <StreakBadge />
        <button className="relative text-slate-400 hover:text-slate-600">
          <Bell size={18} />
          {alerts?.length > 0 && <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-red-500" />}
        </button>
      </div>
    </header>
  );
}
