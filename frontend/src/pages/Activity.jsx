import { useEffect, useState } from 'react';
import { getDashboard, getWorkouts, getWorkoutSummary, getWorkoutTargets, logWorkout } from '../api';
import ActivityNudge from '../components/ActivityNudge';
import ChatInterface from '../components/ChatInterface';
import StepProgressRing from '../components/StepProgressRing';
import WorkoutLog from '../components/WorkoutLog';
import WorkoutSummary from '../components/WorkoutSummary';
import WorkoutTargets from '../components/WorkoutTargets';
import useStore from '../store';

export default function ActivityPage() {
  const { selectedUserId, dashboard, showToast, setDashboard } = useStore();
  const [workouts, setWorkouts] = useState([]);
  const [summary, setSummary] = useState(dashboard?.workout_summary);
  const [targets, setTargets] = useState(dashboard?.workout_targets);
  const workoutOptions = [
    { label: 'Running', value: 'running' },
    { label: 'Walking', value: 'walking' },
    { label: 'Cycling', value: 'cycling' },
    { label: 'Swimming', value: 'swimming' },
    { label: 'Yoga', value: 'yoga' },
    { label: 'Strength Training', value: 'weight_training' },
    { label: 'HIIT', value: 'hiit' },
    { label: 'Other', value: 'other' }
  ];
  const [form, setForm] = useState({ type: 'running', duration_min: 30, calories: '' });
  const coachContext = [
    `User: ${selectedUserId}`,
    `Current steps today: ${dashboard?.metrics?.steps ?? 'unknown'}`,
    `Current step goal: ${dashboard?.step_goal ?? 'unknown'}`,
    `Weather: ${dashboard?.weather?.summary ?? 'unknown'}`,
    `Weather note: ${dashboard?.weather?.note ?? 'none'}`,
    `Workout sessions this week: ${summary?.total_sessions ?? 'unknown'}`,
    `Workout minutes this week: ${summary?.total_minutes ?? 'unknown'}`,
    `Workout calories this week: ${summary?.total_calories ?? 'unknown'}`,
    `Recommended sessions: ${(targets?.recommended_sessions || []).map((session) => `${session.type} ${session.frequency}`).join('; ') || 'none available'}`,
    `Recent workouts: ${workouts.slice(0, 3).map((workout) => `${workout.type} ${workout.duration_min} min on ${workout.date}`).join('; ') || 'none logged'}`
  ].join('\n');

  const load = async () => {
    try {
      const [workoutsResponse, summaryResponse, targetsResponse] = await Promise.all([
        getWorkouts(selectedUserId),
        getWorkoutSummary(selectedUserId),
        getWorkoutTargets(selectedUserId)
      ]);
      setWorkouts(workoutsResponse.data);
      setSummary(summaryResponse.data);
      setTargets(targetsResponse.data);
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  useEffect(() => { load(); }, [selectedUserId, showToast]);

  const submit = async () => {
    try {
      await logWorkout(selectedUserId, { ...form, type: form.type });
      const [dashboardResponse] = await Promise.all([
        getDashboard(selectedUserId),
        load()
      ]);
      setDashboard(dashboardResponse.data);
      showToast('Workout logged');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <StepProgressRing
          current={dashboard?.metrics?.steps || 0}
          goal={dashboard?.step_goal || 7500}
          size={200}
          note={
            dashboard?.metrics?.steps_from_logged_activity
              ? `Includes about ${dashboard.metrics.steps_from_logged_activity.toLocaleString()} step-equivalent from logged walking/running today.`
              : null
          }
        />
        <div className="lg:col-span-2"><WorkoutSummary summary={summary} /></div>
      </div>
      <WorkoutTargets data={targets} />
      <ChatInterface
        chatType="coach"
        userId={selectedUserId}
        title="Workout Coach"
        placeholder="Ask what workouts you should do next"
        helperText="The coach uses your current workout targets, recent sessions, and activity progress from this page."
        suggestedPrompts={[
          'What workout should I do tomorrow based on this week?',
          'Am I doing enough cardio and strength work?',
          'How should I adjust my routine to improve bio age?'
        ]}
        context={coachContext}
      />
      <div className="glass-card p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
            {workoutOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <input type="number" value={form.duration_min} onChange={(event) => setForm({ ...form, duration_min: Number(event.target.value) })} placeholder="Duration (min)" aria-label="Workout duration in minutes" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          <input type="number" value={form.calories} onChange={(event) => setForm({ ...form, calories: Number(event.target.value) })} placeholder="Calories burned" aria-label="Workout calories burned" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          <button onClick={submit} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition">Log Workout</button>
        </div>
      </div>
      <WorkoutLog workouts={workouts} />
      <ActivityNudge currentSteps={dashboard?.metrics?.steps || 0} stepGoal={dashboard?.step_goal || 7500} nudge={dashboard?.activity_nudge} />
    </div>
  );
}
