import { Activity, Apple, Brain, FlaskConical, LayoutDashboard, Lightbulb, PersonStanding, Settings as SettingsIcon, Sparkles, Trophy, Upload, X, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const items = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/ingest', label: 'Data Ingest', icon: Upload },
  { to: '/insights', label: 'Insights', icon: Lightbulb },
  { to: '/research', label: 'Research Lab', icon: FlaskConical },
  { to: '/mental', label: 'Mental Health', icon: Brain },
  { to: '/nutrition', label: 'Nutrition', icon: Apple },
  { to: '/future', label: 'Future Self', icon: Sparkles },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/posture', label: 'Posture', icon: PersonStanding },
  { to: '/gamification', label: 'Gamification', icon: Trophy },
];

const bottomItems = [
  { to: '/family', label: 'Family', icon: Users },
  { to: '/settings', label: 'Settings', icon: SettingsIcon }
];

function LinkItem({ to, label, icon: Icon, onNavigate }) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition border-l-2 ${isActive ? 'bg-emerald-500/10 text-emerald-400 border-emerald-400' : 'border-transparent text-slate-300 hover:bg-white/5 hover:text-white'}`}
    >
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  );
}

export default function Sidebar({ mobileOpen = false, onClose = () => {} }) {
  return (
    <>
      <div className={`fixed inset-0 bg-slate-950/50 z-30 md:hidden transition-opacity ${mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`} onClick={onClose} />
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-gradient-to-b from-slate-900 to-slate-950 text-white border-r border-slate-800 flex flex-col overflow-hidden transition-transform duration-300 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
      <div className="px-6 pt-6 pb-5 border-b border-slate-800 shrink-0">
        <div className="md:hidden flex justify-end mb-4">
          <button type="button" onClick={onClose} className="rounded-full border border-slate-700 p-2 text-slate-300 hover:text-white transition">
            <X size={16} />
          </button>
        </div>
        <img
          src="/eirview-brand.png"
          alt="EirView logo"
          className="w-44 h-auto rounded-2xl bg-white p-2 shadow-lg shadow-slate-950/30 ring-1 ring-emerald-500/20"
        />
        <div className="mt-4">
          <div className="text-2xl font-bold tracking-tight text-white">EirView</div>
          <div className="mt-1 text-sm leading-snug text-slate-300">Health intelligence with a sharper signal.</div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-6">
        <nav className="space-y-1">
          {items.map((item) => <LinkItem key={item.to} {...item} onNavigate={onClose} />)}
        </nav>
        <div className="bg-gradient-to-r from-transparent via-slate-700 to-transparent h-px my-4" />
        <nav className="space-y-1 pb-6">
          {bottomItems.map((item) => <LinkItem key={item.to} {...item} onNavigate={onClose} />)}
        </nav>
      </div>
      </aside>
    </>
  );
}
