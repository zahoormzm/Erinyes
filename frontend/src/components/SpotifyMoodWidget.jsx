import { Cloud, CloudRain, Music2, Sun, TriangleAlert, Zap } from 'lucide-react';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

const icons = {
  sun: Sun,
  cloud: Cloud,
  zap: Zap,
  'cloud-rain': CloudRain,
};

function Meter({ label, value }) {
  const pct = Math.max(0, Math.min((Number(value) || 0) * 100, 100));
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
        <span>{label}</span>
        <span>{Number(value || 0).toFixed(2)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-amber-400" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function SpotifyMoodWidget({ spotifyMood }) {
  const navigate = useNavigate();
  const emotion = spotifyMood?.emotion_class;
  const Icon = icons[emotion?.icon] || Music2;
  const melancholicStreak = useMemo(() => {
    const history = spotifyMood?.history || [];
    return history.slice(0, 3).every((entry) => entry?.emotion_class?.emotion === 'melancholic');
  }, [spotifyMood]);

  if (!spotifyMood?.available) {
    return (
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-5">
        <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">Spotify Mood</div>
        <div className="mt-3 text-sm text-slate-500">Spotify isn’t connected yet for this profile.</div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => navigate('/mental')}
      className="w-full text-left bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-500">
        <Music2 size={16} className="text-emerald-500" />
        Spotify Mood
      </div>
      <div className={`mt-4 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium ${emotion?.bg_color || 'bg-slate-50'} ${emotion?.border_color || 'border-slate-200'}`}>
        <Icon size={16} style={{ color: emotion?.color }} />
        <span className="text-slate-800">{emotion?.label || 'Unknown Mood'}</span>
      </div>
      <div className="mt-4 space-y-3">
        <Meter label="Mood" value={spotifyMood?.avg_valence} />
        <Meter label="Energy" value={spotifyMood?.avg_energy} />
      </div>
      <div className="mt-4 text-xs text-slate-500">Based on your last {spotifyMood?.track_count || 20} tracks</div>
      {melancholicStreak ? (
        <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <TriangleAlert size={16} className="mt-0.5 shrink-0" />
          <span>Your music suggests a mood dip this week.</span>
        </div>
      ) : null}
    </button>
  );
}
