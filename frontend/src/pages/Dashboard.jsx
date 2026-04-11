import { Activity, CloudSun, Droplets, Footprints, Heart, Moon, ShieldAlert, Timer, TrendingUp, Wind } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getSpotifyMood } from '../api';
import FormulaTooltip from '../components/FormulaTooltip';
import MetricCard from '../components/MetricCard';
import ReminderCards from '../components/ReminderCards';
import SpecialistCards from '../components/SpecialistCards';
import SpotifyMoodWidget from '../components/SpotifyMoodWidget';
import WorkoutSummary from '../components/WorkoutSummary';
import useStore from '../store';

function BioAgeRing({ value, chrono }) {
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const gap = value - chrono;
  const tone = gap <= 0 ? '#10b981' : gap <= 3 ? '#f59e0b' : '#ef4444';
  const progress = Math.max(0.1, Math.min(value / Math.max(chrono + 10, value + 4, 1), 1));

  return (
    <div className="relative w-40 h-40 shrink-0">
      <svg viewBox="0 0 160 160" className="w-full h-full -rotate-90">
        <circle cx="80" cy="80" r={radius} stroke="#e2e8f0" strokeWidth="14" fill="none" />
        <circle
          cx="80"
          cy="80"
          r={radius}
          stroke={tone}
          strokeWidth="14"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <div className="text-4xl font-bold tabular-nums text-slate-900">{Number(value || 0).toFixed(1)}</div>
        <div className="text-sm text-slate-500 mt-1">years</div>
        <div className={`text-xs font-medium mt-2 ${gap <= 0 ? 'text-emerald-600' : gap <= 3 ? 'text-amber-600' : 'text-red-600'}`}>
          {gap <= 0 ? `${Math.abs(gap).toFixed(1)} younger` : `${gap.toFixed(1)} older`}
        </div>
      </div>
    </div>
  );
}

function SubsystemHeroRows({ dashboard, selectedUserId }) {
  const chrono = Number(dashboard?.profile?.age || 0);
  const rows = [
    ['cardiovascular', 'Cardiovascular', dashboard?.bio_age?.cardiovascular],
    ['metabolic', 'Metabolic', dashboard?.bio_age?.metabolic],
    ['musculoskeletal', 'Musculoskeletal', dashboard?.bio_age?.musculoskeletal],
    ['neurological', 'Neurological', dashboard?.bio_age?.neurological],
  ];
  const max = Math.max(...rows.map(([, , value]) => Number(value || 0)), chrono + 5, 1);

  return (
    <div className="space-y-4">
      {rows.map(([key, label, value]) => {
        const numeric = Number(value || chrono);
        const pct = (numeric / max) * 100;
        const delta = numeric - chrono;
        const color = delta <= 0 ? 'bg-emerald-500' : delta <= 3 ? 'bg-amber-500' : 'bg-red-500';
        return (
          <div key={key}>
            <div className="flex items-center justify-between gap-3 text-sm mb-1.5">
              <span className="font-medium text-slate-700">{label}</span>
              <FormulaTooltip userId={selectedUserId} metric={`bio_age_${key}`}>
                <span className="font-semibold tabular-nums text-slate-900">{numeric.toFixed(1)}</span>
              </FormulaTooltip>
            </div>
            <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
              <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
            </div>
            <div className={`text-xs mt-1 ${delta <= 0 ? 'text-emerald-600' : delta <= 3 ? 'text-amber-600' : 'text-red-600'}`}>
              {delta === 0 ? 'Aligned with chronological age' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}yr`}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function Dashboard() {
  const { dashboard, selectedUserId } = useStore();
  const [spotifyMood, setSpotifyMood] = useState(null);

  useEffect(() => {
    if (!selectedUserId) return;
    (async () => {
      try {
        const response = await getSpotifyMood(selectedUserId);
        setSpotifyMood(response.data);
      } catch {
        setSpotifyMood({ available: false });
      }
    })();
  }, [selectedUserId]);

  const metrics = dashboard?.metrics || {};
  const metricCards = useMemo(() => [
    ['Resting HR', metrics.resting_hr, 'bpm', Heart, metrics.resting_hr < 70 ? 'good' : 'warning', 'Healthy: under 70 bpm'],
    ['HRV', metrics.hrv, 'ms', Activity, metrics.hrv > 40 ? 'good' : 'warning', 'Higher is better — aim for 40+ ms'],
    ['Steps', metrics.steps, 'steps', Footprints, metrics.steps > 7500 ? 'good' : 'warning', 'Goal: 7,500+ steps/day'],
    ['Sleep', metrics.sleep, 'hours', Moon, metrics.sleep >= 7 ? 'good' : 'warning', 'Aim for 7–9 hours'],
    ['VO2max', metrics.vo2max, 'mL/kg/min', Wind, metrics.vo2max > 40 ? 'good' : 'warning', 'Good fitness: 40+ mL/kg/min'],
    ['SpO2', metrics.spo2, '%', Droplets, metrics.spo2 > 95 ? 'good' : 'warning', 'Normal: 95–100%'],
    ['Exercise Minutes', metrics.exercise_min, 'min', Timer, metrics.exercise_min > 30 ? 'good' : 'warning', 'WHO recommends 30+ min/day'],
    ['Flights Climbed', metrics.flights, 'flights', TrendingUp, 'neutral', ''],
  ], [metrics]);

  if (!dashboard) {
    return <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="bg-slate-200 animate-pulse rounded-2xl h-32" />)}</div>;
  }

  if (!dashboard.profile) {
    return <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-8 text-center text-slate-500">No health data yet. Go to Data Ingest to add your first data.</div>;
  }

  const chrono = Number(dashboard.profile?.age || 0);
  const overall = Number(dashboard.bio_age?.overall || dashboard.bio_age_overall || chrono);
  const gap = overall - chrono;
  const userName = dashboard.profile?.name?.split(' ')[0] || 'there';

  const summaryLine = gap <= -2
    ? `Your body is aging slower than average — ${Math.abs(gap).toFixed(1)} years younger biologically. Keep it up.`
    : gap <= 0
      ? `You're right on track — your biological age closely matches your chronological age.`
      : gap <= 3
        ? `Your biological age is slightly above your real age. Small changes can close this gap.`
        : `Your biological age is ${gap.toFixed(1)} years above your real age — let's work on bringing it down.`;

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 px-6 py-6 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.15),transparent_50%)]" />
        <div className="relative">
          <div className="text-2xl font-semibold tracking-tight">Hey {userName}</div>
          <div className="mt-2 text-sm text-slate-300 max-w-2xl leading-relaxed">{summaryLine}</div>
          {dashboard.cross_domain_insight ? (
            <div className="mt-3 text-sm text-emerald-200/90 leading-relaxed">{dashboard.cross_domain_insight}</div>
          ) : null}
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6 hover:shadow-md transition-shadow">
        <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">Your Biological Age</div>
        <div className="grid grid-cols-1 xl:grid-cols-[220px_1fr] gap-8 mt-5 items-center">
          <div className="flex flex-col items-center xl:items-start">
            <FormulaTooltip userId={selectedUserId} metric="bio_age_overall">
              <div>
                <BioAgeRing value={overall} chrono={chrono} />
              </div>
            </FormulaTooltip>
            <div className="mt-4 text-sm text-slate-500">
              chrono: <span className="font-medium text-slate-900">{chrono}</span> | face: <span className="font-medium text-slate-900">{dashboard.face_age ? Number(dashboard.face_age).toFixed(1) : '—'}</span>
            </div>
          </div>
          <div>
            <SubsystemHeroRows dashboard={dashboard} selectedUserId={selectedUserId} />
          </div>
        </div>
      </div>

      <ReminderCards />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {metricCards.map(([label, value, unit, icon, status, hint]) => (
          <MetricCard key={label} label={label} value={value} unit={unit} icon={icon} status={status} hint={hint} compact />
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-8">
          <WorkoutSummary summary={dashboard.workout_summary} compact />
        </div>
        <div className="xl:col-span-4 space-y-4">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-5 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-500">
                <CloudSun size={16} className="text-sky-600" />
                Outdoor Conditions
              </div>
              <div className={`text-[11px] font-semibold uppercase tracking-wide ${dashboard.weather?.outdoor_ok ? 'text-emerald-700' : 'text-amber-700'}`}>
                {dashboard.weather?.label || 'Conditions unavailable'}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4 text-center">
              <div className="glass-subcard py-2">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Temp</div>
                <div className="text-sm font-semibold text-slate-900 mt-1">{dashboard.weather?.temp_c != null ? `${Math.round(dashboard.weather.temp_c)}°C` : '—'}</div>
              </div>
              <div className="glass-subcard py-2">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">AQI</div>
                <div className="text-sm font-semibold text-slate-900 mt-1">{dashboard.weather?.aqi ?? '—'}</div>
              </div>
              <div className="glass-subcard py-2">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">UV</div>
                <div className="text-sm font-semibold text-slate-900 mt-1">{dashboard.weather?.uv_index != null ? Math.round(dashboard.weather.uv_index) : '—'}</div>
              </div>
            </div>
            <div className="mt-3 text-sm text-slate-700">{dashboard.weather?.summary || dashboard.weather?.description || 'Weather context unavailable.'}</div>
            {dashboard.weather?.location_label ? (
              <div className="mt-2 text-xs text-slate-500">
                Weather source: {dashboard.weather.location_label}
              </div>
            ) : null}
            {dashboard.weather?.note ? (
              <div className="mt-2 inline-flex items-start gap-2 text-xs text-slate-500">
                <ShieldAlert size={13} className="mt-0.5 text-slate-400" />
                <span>{dashboard.weather.note}</span>
              </div>
            ) : null}
          </div>
          <SpotifyMoodWidget spotifyMood={spotifyMood} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-7">
          <SpecialistCards compact />
        </div>
        <div className="xl:col-span-5">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-5 hover:shadow-md transition-shadow">
            <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">Trajectory Snapshot</div>
            <div className="mt-3 text-sm text-slate-600 leading-relaxed">{dashboard.narrative}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
