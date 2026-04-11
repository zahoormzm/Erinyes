import { useEffect, useState } from 'react';
import { simulate } from '../api';
import useStore from '../store';

export default function HabitSliders() {
  const { selectedUserId, profile, showToast, setInsightSimulation } = useStore();
  const [values, setValues] = useState({
    sleep: profile?.sleep_hours || 7,
    exercise: profile?.exercise_hours_week || 4,
    diet: profile?.diet_quality === 'excellent' ? 4 : profile?.diet_quality === 'good' ? 3 : profile?.diet_quality === 'poor' ? 1 : 2,
    stress: profile?.stress_level || 5,
    screen_time: profile?.screen_time_hours || 6,
    exam_stress: profile?.exam_stress || 5,
    duration: '6m'
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const mapDiet = { 1: 'Poor', 2: 'Average', 3: 'Good', 4: 'Excellent' };
  const durationOptions = [
    { value: '1w', label: '1 week' },
    { value: '1m', label: '1 month' },
    { value: '3m', label: '3 months' },
    { value: '6m', label: '6 months' }
  ];

  useEffect(() => {
    setValues({
      sleep: profile?.sleep_hours || 7,
      exercise: profile?.exercise_hours_week || 4,
      diet: profile?.diet_quality === 'excellent' ? 4 : profile?.diet_quality === 'good' ? 3 : profile?.diet_quality === 'poor' ? 1 : 2,
      stress: profile?.stress_level || 5,
      screen_time: profile?.screen_time_hours || 6,
      exam_stress: profile?.exam_stress || 5,
      duration: '6m'
    });
    setResult(null);
  }, [profile]);

  const update = (key, value) => setValues((previous) => ({ ...previous, [key]: ['duration'].includes(key) ? value : Number(value) }));

  const onSimulate = async () => {
    try {
      setLoading(true);
      const response = await simulate(selectedUserId, values);
      setResult(response.data.simulation);
      setInsightSimulation({
        changes: values,
        simulation: response.data.simulation,
        narrative: response.data.narrative || '',
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const row = (label, key, min, max, step, formatter = (value) => value) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className="text-sm text-slate-500">{formatter(values[key])}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={values[key]} onChange={(event) => update(key, event.target.value)} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-500" />
    </div>
  );

  return (
    <div className="glass-card p-6">
      <div className="mb-4">
        <div className="text-lg font-semibold text-slate-900">Try a What-If Scenario</div>
        <div className="text-sm text-slate-600 mt-1">
          These sliders do not change your saved profile. They only generate a hypothetical scenario you can compare against your current baseline.
        </div>
      </div>
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">Scenario duration</span>
            <span className="text-sm text-slate-500">{durationOptions.find((option) => option.value === values.duration)?.label || '6 months'}</span>
          </div>
          <select
            value={values.duration}
            onChange={(event) => update('duration', event.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          >
            {durationOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>
        {row('Sleep (hours)', 'sleep', 4, 10, 0.5)}
        {row('Exercise (hours/week)', 'exercise', 0, 14, 1)}
        {row('Diet Quality', 'diet', 1, 4, 1, (value) => mapDiet[value])}
        {row('Stress Level', 'stress', 1, 10, 1)}
        {row('Screen Time (hours)', 'screen_time', 0, 16, 1)}
        {profile?.academic_year && profile.academic_year !== 'Not a student' && row('Academic Stress', 'exam_stress', 1, 10, 1)}
      </div>
      <button onClick={onSimulate} disabled={loading} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-6 py-2.5 font-medium transition mt-4 disabled:opacity-60">
        {loading ? 'Simulating...' : 'Simulate'}
      </button>
      {result && (
        <div className={`mt-4 rounded-2xl p-4 border ${result.improvement >= 0 ? 'bg-emerald-50/90 border-emerald-200' : 'bg-red-50/90 border-red-200'}`}>
          <div className={`${result.improvement >= 0 ? 'text-emerald-700' : 'text-red-700'} font-medium`}>
            Bio age: {result.current.overall} -&gt; {result.projected.overall} ({result.improvement >= 0 ? `improvement: ${result.improvement} years` : `worse by ${Math.abs(result.improvement)} years`})
          </div>
          <div className="text-xs text-slate-600 mt-2">
            Scenario assumes you sustain these settings for {result.duration?.label || '6 months'}. Read the detailed interpretation cards below. Future Self will also use your latest simulated scenario.
          </div>
        </div>
      )}
    </div>
  );
}
