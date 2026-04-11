import { Brain, Clock3, FileText, RefreshCcw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { getDashboard, updateProfile } from '../api';
import useStore from '../store';

const PHQ9_QUESTIONS = [
  'Little interest or pleasure in doing things',
  'Feeling down, depressed, or hopeless',
  'Trouble falling asleep, staying asleep, or sleeping too much',
  'Feeling tired or having little energy',
  'Poor appetite or overeating',
  'Feeling bad about yourself or that you have let yourself or your family down',
  'Trouble concentrating on things, such as reading or studying',
  'Moving or speaking so slowly that other people could notice, or being unusually fidgety or restless',
  'Thoughts that you would be better off dead or of hurting yourself in some way',
];

const PHQ9_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
];

function getSeverity(score) {
  if (score == null) return { label: 'Not calibrated', tone: 'text-slate-600 bg-slate-100 border-slate-200' };
  if (score <= 4) return { label: 'Minimal', tone: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
  if (score <= 9) return { label: 'Mild', tone: 'text-lime-700 bg-lime-50 border-lime-200' };
  if (score <= 14) return { label: 'Moderate', tone: 'text-amber-700 bg-amber-50 border-amber-200' };
  if (score <= 19) return { label: 'Moderately severe', tone: 'text-orange-700 bg-orange-50 border-orange-200' };
  return { label: 'Severe', tone: 'text-red-700 bg-red-50 border-red-200' };
}

function formatTimestamp(value) {
  if (!value) return 'Not calibrated yet';
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? value.replace(' ', 'T') + 'Z' : value;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function getDaysSince(value) {
  if (!value) return null;
  const parsed = new Date(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? value.replace(' ', 'T') + 'Z' : value);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.max(Math.floor((Date.now() - parsed.getTime()) / 86400000), 0);
}

export default function PHQ9CalibrationCard({
  title = 'PHQ-9 Calibration',
  description = 'PHQ-9 is not inferred from chat. This baseline only changes when you answer the questionnaire again.',
  className = '',
  onCalibrated,
}) {
  const { selectedUserId, profile, setProfile, setDashboard, showToast } = useStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [answers, setAnswers] = useState(() => Array(PHQ9_QUESTIONS.length).fill(null));
  const [saving, setSaving] = useState(false);

  const score = profile?.phq9_score == null ? null : Number(profile.phq9_score);
  const calibratedAt = profile?.phq9_last_calibrated_at || null;
  const answeredCount = answers.filter((value) => value != null).length;
  const liveScore = answers.reduce((total, value) => total + (value ?? 0), 0);
  const daysSinceCalibration = getDaysSince(calibratedAt);
  const needsCalibration = score == null;
  const hasLegacyScore = score != null && !calibratedAt;
  const shouldRecalibrate = daysSinceCalibration == null ? true : daysSinceCalibration >= 14;
  const severity = useMemo(() => getSeverity(score), [score]);

  const openCalibration = () => {
    setAnswers(Array(PHQ9_QUESTIONS.length).fill(null));
    setModalOpen(true);
  };

  const saveCalibration = async () => {
    if (answers.some((value) => value == null)) {
      showToast('Answer all 9 PHQ-9 questions before saving.', 'error');
      return;
    }
    setSaving(true);
    try {
      const total = answers.reduce((sum, value) => sum + value, 0);
      const profileResponse = await updateProfile(selectedUserId, { phq9_score: total });
      const nextProfile = profileResponse.data?.profile || { ...profile, phq9_score: total };
      setProfile(nextProfile);
      try {
        const dashboardResponse = await getDashboard(selectedUserId);
        setDashboard(dashboardResponse.data);
      } catch {
        // The saved profile is the source of truth; dashboard can refresh on the next page load if needed.
      }
      onCalibrated?.();
      setModalOpen(false);
      showToast(`PHQ-9 calibrated at ${total}/27.`);
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className={`glass-card p-5 ${className}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              <Brain size={14} />
              Mental Baseline
            </div>
            <div>
              <div className="text-lg font-semibold text-slate-900">{title}</div>
              <div className="mt-1 text-sm leading-relaxed text-slate-600 max-w-2xl">{description}</div>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium ${severity.tone}`}>
                <FileText size={15} />
                {score == null ? 'No PHQ-9 score saved yet' : `Current score ${score}/27 · ${severity.label}`}
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-1.5 text-sm text-slate-600">
                <Clock3 size={15} />
                {formatTimestamp(calibratedAt)}
              </div>
            </div>
            <div className={`rounded-2xl border px-4 py-3 text-sm ${
              needsCalibration || shouldRecalibrate
                ? 'border-amber-200 bg-amber-50 text-amber-800'
                : 'border-emerald-200 bg-emerald-50 text-emerald-800'
            }`}>
              {needsCalibration
                ? 'No PHQ-9 baseline is saved for this profile yet. Mental wellness and neuro-age are currently using an empty PHQ-9 input.'
                : hasLegacyScore
                  ? 'This profile has a legacy PHQ-9 score but no recorded questionnaire date. Calibrate once so the score is tied to an explicit assessment.'
                : shouldRecalibrate
                  ? `This PHQ-9 baseline is ${daysSinceCalibration ?? 0} days old. Recalibrating keeps the score tied to the last two weeks instead of an outdated baseline.`
                  : 'This calibrated PHQ-9 baseline stays in place until you choose to recalibrate it again.'}
            </div>
          </div>
          <div className="flex flex-col gap-2 lg:min-w-[220px]">
            <button
              type="button"
              onClick={openCalibration}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-600"
            >
              <RefreshCcw size={16} />
              {score == null ? 'Calibrate PHQ-9' : 'Recalibrate PHQ-9'}
            </button>
            <div className="text-xs leading-relaxed text-slate-500">
              Answers cover the last two weeks. Recalibration updates the saved PHQ-9 score and the reminder timeline.
            </div>
          </div>
        </div>
      </div>

      {modalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4">
          <div className="glass-card max-h-[90vh] w-full max-w-4xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-200/70 px-6 py-5">
              <div>
                <div className="text-xl font-semibold text-slate-900">PHQ-9 Calibration</div>
                <div className="mt-1 text-sm text-slate-500">Over the last two weeks, how often have you been bothered by the following problems?</div>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
              >
                Close
              </button>
            </div>

            <div className="max-h-[calc(90vh-158px)] space-y-4 overflow-y-auto px-6 py-5">
              <div className="glass-subcard flex flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-slate-600">
                  Answered {answeredCount} of {PHQ9_QUESTIONS.length} questions.
                </div>
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700">
                  Live total {liveScore}/27
                </div>
              </div>

              {PHQ9_QUESTIONS.map((question, index) => (
                <div key={question} className="glass-subcard px-4 py-4">
                  <div className="text-sm font-semibold text-slate-900">{index + 1}. {question}</div>
                  <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
                    {PHQ9_OPTIONS.map((option) => {
                      const active = answers[index] === option.value;
                      return (
                        <button
                          key={option.label}
                          type="button"
                          onClick={() => setAnswers((previous) => previous.map((value, valueIndex) => (valueIndex === index ? option.value : value)))}
                          className={`rounded-2xl border px-3 py-3 text-left text-sm transition ${
                            active
                              ? 'border-emerald-400 bg-emerald-50 text-emerald-800 shadow-sm'
                              : 'border-slate-200 bg-white/80 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                          }`}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                Question 9 can flag immediate safety risk. If you are in immediate danger or think you may act on self-harm thoughts, contact local emergency services or a crisis hotline right away.
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-slate-200/70 px-6 py-5 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-slate-500">This saves a persistent PHQ-9 baseline for the selected profile until you recalibrate again.</div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={saveCalibration}
                  disabled={saving}
                  className="rounded-2xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? 'Saving...' : 'Save Calibration'}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
