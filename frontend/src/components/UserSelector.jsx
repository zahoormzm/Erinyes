import { ChevronDown, UserCircle2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import useStore from '../store';

export default function UserSelector() {
  const { users, selectedUserId, setSelectedUser } = useStore();
  const [open, setOpen] = useState(false);
  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) || null,
    [users, selectedUserId]
  );

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="glass-subcard min-w-[220px] px-3 py-2 text-left hover:border-emerald-300"
      >
        <div className="flex items-center gap-3">
          <UserCircle2 size={20} className="text-slate-400" />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-slate-800">{selectedUser?.name || 'Select user'}</div>
            <div className="truncate text-xs text-slate-500">{selectedUser?.id || 'No active user'}{selectedUser?.age ? ` • ${selectedUser.age} yrs` : ''}</div>
          </div>
          <ChevronDown size={16} className={`text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>
      {open && (
        <div className="glass-card absolute right-0 z-50 mt-2 w-[320px] p-3 shadow-xl">
          <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Switch Profile</div>
          <div className="space-y-2">
            {users.map((user) => (
              <button
                key={user.id}
                type="button"
                onClick={() => {
                  setSelectedUser(user.id);
                  setOpen(false);
                }}
                className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                  user.id === selectedUserId
                    ? 'border-emerald-400 bg-emerald-50/90'
                    : 'border-slate-200 bg-slate-50/70 hover:border-emerald-200 hover:bg-slate-50/90'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-800">{user.name}</div>
                    <div className="text-xs text-slate-500">{user.id} • {user.sex || 'sex n/a'}{user.age ? ` • ${user.age} yrs` : ''}</div>
                  </div>
                  <div className="text-xs font-medium text-emerald-700">
                    {user.id === selectedUserId ? 'Active' : 'Switch'}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
