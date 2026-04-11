import { GraduationCap, MessageCircleHeart } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getSpotifyMood } from '../api';
import ChatInterface from '../components/ChatInterface';
import PHQ9CalibrationCard from '../components/PHQ9CalibrationCard';
import SpotifyMoodWidget from '../components/SpotifyMoodWidget';
import WellnessGauge from '../components/WellnessGauge';
import useStore from '../store';

const suggestedTopics = [
  "I've been feeling overwhelmed",
  'My sleep has been off',
  "I'm stressed about exams",
  'I just want to talk',
];

export default function Mental() {
  const { dashboard, selectedUserId, profile } = useStore();
  const [spotifyMood, setSpotifyMood] = useState(null);
  const [chatActive, setChatActive] = useState(false);
  const [initialMessage, setInitialMessage] = useState('');

  useEffect(() => {
    if (!selectedUserId) return;
    setChatActive(false);
    setInitialMessage('');
    (async () => {
      try {
        const response = await getSpotifyMood(selectedUserId);
        setSpotifyMood(response.data);
      } catch {
        setSpotifyMood({ available: false });
      }
    })();
  }, [selectedUserId]);

  const openChat = (message) => {
    setChatActive(true);
    setInitialMessage(message);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
      <div className="space-y-4">
        <PHQ9CalibrationCard />
        <WellnessGauge userId={selectedUserId} score={dashboard?.wellness_score || 0} breakdown={dashboard?.wellness_breakdown || []} />
        <SpotifyMoodWidget spotifyMood={spotifyMood} />
        {spotifyMood?.available && ['melancholic', 'tense'].includes(spotifyMood?.emotion_class?.emotion) ? (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-amber-200 shadow-sm p-4 text-sm text-amber-800">
            Your music patterns may be reflecting or reinforcing your current mood.
          </div>
        ) : null}
        {profile?.academic_year ? (
          <div className="bg-amber-50/80 backdrop-blur-sm border border-amber-200 rounded-2xl p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-amber-800"><GraduationCap size={16} /> Academic Pressure</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="bg-white rounded-full px-3 py-1 text-sm font-medium">GPA {profile.academic_gpa ?? '—'}</span>
              <span className="bg-white rounded-full px-3 py-1 text-sm font-medium">{profile.study_hours_daily ?? '—'}h/day</span>
            </div>
            <div className="mt-3 text-sm text-amber-700">Academic year: {profile.academic_year}</div>
            {profile.exam_stress > 7 ? <div className="text-amber-700 text-xs mt-2">High academic stress detected — this may be affecting your overall wellness score.</div> : null}
            {profile.exam_stress > 7 && profile.sleep_hours < 6 ? <div className="text-red-600 text-xs mt-1 font-medium">Burnout risk: high study load plus insufficient sleep.</div> : null}
          </div>
        ) : null}
      </div>

      {!chatActive ? (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6 lg:p-8 min-h-[580px] overflow-hidden relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.12),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(56,189,248,0.08),transparent_25%)]" />
          <div className="relative h-full flex flex-col justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-emerald-700">
                <MessageCircleHeart size={14} />
                Mental Health
              </div>
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-slate-900">How are you feeling today?</h2>
              <p className="mt-3 text-sm text-slate-600 leading-relaxed max-w-xl">
                This space connects your mood to sleep, stress, nutrition, Spotify patterns, and recovery signals. Start gently and let the chat open from your current data instead of a blank screen.
              </p>
            </div>
            <div className="mt-10">
              <button
                type="button"
                onClick={() => openChat('__INIT__')}
                className="inline-flex items-center gap-2 rounded-full bg-emerald-500 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-600 transition"
              >
                Let&apos;s Talk →
              </button>
              <div className="mt-8">
                <div className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3">Suggested topics</div>
                <div className="flex flex-wrap gap-3">
                  {suggestedTopics.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => openChat(prompt)}
                      className="group flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 transition-all"
                    >
                      <span className="text-slate-400 group-hover:text-emerald-500 transition">→</span>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <ChatInterface
          chatType="mental"
          userId={selectedUserId}
          title="Mental Health Chat"
          placeholder="How are you feeling today?"
          helperText="Use this chat for stress, burnout, mood, routines, sleep-linked wellbeing, and emotional reflection. Unrelated questions are intentionally blocked."
          suggestedPrompts={suggestedTopics}
          initialMessage={initialMessage}
          tall
        />
      )}
    </div>
  );
}
