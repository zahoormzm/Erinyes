import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function WorkoutSummary({ summary, compact = false }) {
  if (!summary) {
    return <div className="glass-card p-6 text-sm text-slate-500">Workout summary unavailable.</div>;
  }
  return (
    <div className={`glass-card ${compact ? 'p-4' : 'p-6'}`}>
      <ResponsiveContainer width="100%" height={compact ? 160 : 250}>
        <BarChart data={summary.chart || []}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="day" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="minutes" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className={`${compact ? 'text-xs mt-2' : 'text-sm mt-3'} text-slate-600`}>{summary.total_sessions} sessions | {summary.total_minutes} total minutes | {summary.total_calories} calories burned this week</div>
    </div>
  );
}
