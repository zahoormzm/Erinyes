import { Flame, Sparkles, Trophy } from 'lucide-react';
import AchievementGrid from '../components/AchievementGrid';
import DailyChecklist from '../components/DailyChecklist';
import Leaderboard from '../components/Leaderboard';
import WeeklyChallenge from '../components/WeeklyChallenge';
import XPBar from '../components/XPBar';
import useStore from '../store';

export default function GamificationPage() {
  const { gamification } = useStore();
  const currentXP = gamification?.total_xp || 0;
  const nextLevelXP = currentXP + (gamification?.xp_to_next_level || 100);
  const achievements = gamification?.achievements || [];
  const activeChallenge = gamification?.active_challenge;
  const streak = gamification?.current_streak || 0;
  const weeklyProgress = activeChallenge?.target
    ? Math.min(Math.round(((activeChallenge?.progress || 0) / activeChallenge.target) * 100), 100)
    : 0;
  const statCards = [
    {
      label: 'Unlocked',
      value: `${achievements.length}/5`,
      note: achievements.length ? 'Badges earned so far' : 'Your first badge is one action away',
      icon: Trophy
    },
    {
      label: 'Momentum',
      value: `${streak} days`,
      note: streak ? 'Current streak is active' : 'Complete 3 actions today to restart',
      icon: Flame
    },
    {
      label: 'Challenge',
      value: activeChallenge?.target ? `${weeklyProgress}%` : 'Waiting',
      note: activeChallenge?.name || 'No weekly challenge loaded yet',
      icon: Sparkles
    }
  ];

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 p-6 md:p-8 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.24),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(56,189,248,0.16),transparent_32%)]" />
        <div className="relative grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <div>
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-200/80">Gamification</div>
            <div className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Keep the streak alive before tonight ends.
            </div>
            <div className="mt-3 max-w-2xl text-sm text-slate-200/90 md:text-base">
              Your rewards layer now mirrors the rest of the app: softer glass surfaces, clearer progress, and badges that visually wake up when you unlock them.
            </div>
            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {statCards.map(({ label, value, note, icon: Icon }) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/10 px-4 py-4 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-300">
                    <Icon size={14} className="text-emerald-300" />
                    {label}
                  </div>
                  <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
                  <div className="mt-1 text-xs text-slate-300">{note}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5 backdrop-blur-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-300">Streak map</div>
                <div className="mt-1 text-2xl font-semibold">{streak}-day streak</div>
              </div>
              <div className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-medium text-emerald-200">
                {streak ? 'On track' : 'Needs a reset'}
              </div>
            </div>
            <div className="mt-5 grid grid-cols-7 gap-2">
              {Array.from({ length: 35 }).map((_, index) => (
                <div
                  key={index}
                  className={`h-6 rounded-xl border ${
                    index < streak
                      ? 'border-emerald-300/40 bg-gradient-to-br from-emerald-300 to-emerald-500 shadow-[0_0_18px_rgba(16,185,129,0.28)]'
                      : 'border-white/10 bg-white/8'
                  }`}
                />
              ))}
            </div>
            <div className="mt-4 text-xs text-slate-300">
              Each filled tile represents a day where you completed the daily action threshold.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <XPBar level={gamification?.level} levelName={gamification?.level_name} currentXP={currentXP} nextLevelXP={nextLevelXP} />
        <div className="glass-card glass-card-hover lg:col-span-2 p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-slate-500">Current season</div>
              <div className="mt-2 text-2xl font-semibold text-slate-900">{gamification?.level_name || 'Health Rookie'}</div>
              <div className="mt-2 text-sm text-slate-600">
                {activeChallenge?.name
                  ? `Your live weekly push is "${activeChallenge.name}". Keep pressure on before the window resets.`
                  : 'Your next badge and next level both move when you close today’s checklist.'}
              </div>
            </div>
            <div className="glass-subcard min-w-[220px] px-4 py-4">
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                <span>Weekly challenge</span>
                <span>{weeklyProgress}%</span>
              </div>
              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200/80">
                <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-emerald-500" style={{ width: `${weeklyProgress}%` }} />
              </div>
              <div className="mt-3 text-sm font-medium text-slate-800">{activeChallenge?.name || 'Move 5 Days'}</div>
              <div className="mt-1 text-xs text-slate-500">
                {(activeChallenge?.progress || 0)}/{activeChallenge?.target || 5} days completed
              </div>
            </div>
          </div>
        </div>
      </div>
      <DailyChecklist />
      <WeeklyChallenge name="Move 5 Days" description="Hit your movement target on 5 days this week." current={gamification?.active_challenge?.progress || 3} target={gamification?.active_challenge?.target || 5} />
      <AchievementGrid achievements={gamification?.achievements || []} />
      <Leaderboard />
    </div>
  );
}
