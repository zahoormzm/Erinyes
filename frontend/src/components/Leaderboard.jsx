import { useEffect, useState } from 'react';
import { getLeaderboard } from '../api';
import useStore from '../store';

export default function Leaderboard() {
  const [rows, setRows] = useState([]);
  const { showToast } = useStore();

  useEffect(() => {
    (async () => {
      try {
        const response = await getLeaderboard();
        setRows(Array.isArray(response.data) ? response.data : response.data.leaderboard || []);
      } catch (error) {
        showToast(error.message, 'error');
      }
    })();
  }, [showToast]);

  return (
    <div className="glass-card p-6 overflow-x-auto">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-slate-900">Leaderboard</div>
          <div className="text-sm text-slate-600">XP, streak, and biological-age momentum across active profiles.</div>
        </div>
      </div>
      {rows.length ? (
        <table className="mt-5 w-full">
          <thead>
            <tr>
              {['#', 'Name', 'Level', 'Streak', 'XP', 'Bio Age Delta'].map((header) => <th key={header} className="text-xs text-slate-500 uppercase tracking-wide font-medium text-left py-3 border-b border-slate-200">{header}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.user_id} className="border-b border-slate-100">
                <td className={`py-3 font-medium ${index === 0 ? 'text-amber-500' : 'text-slate-900'}`}>{index + 1}</td>
                <td className="py-3 text-sm text-slate-700">{row.name}</td>
                <td className="py-3 text-sm text-slate-600">{row.level_name}</td>
                <td className="py-3 text-sm">🔥 {row.current_streak}</td>
                <td className="py-3 font-mono text-sm text-slate-700">{row.total_xp}</td>
                <td className={`py-3 font-mono text-sm ${row.bio_age_delta < 0 ? 'text-emerald-600' : 'text-red-600'}`}>{row.bio_age_delta ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="empty-state-card mt-5 px-4 py-5 text-sm text-slate-600">
          No leaderboard data yet. As soon as at least one profile has gamification stats, rankings will appear here.
        </div>
      )}
    </div>
  );
}
