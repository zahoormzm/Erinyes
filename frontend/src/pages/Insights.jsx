import HabitSliders from '../components/HabitSliders';
import RiskChart from '../components/RiskChart';
import WorkoutTargets from '../components/WorkoutTargets';
import useStore from '../store';

function findYear(rows = [], year = 10) {
  return rows.find((row) => Number(row?.year) === year) || rows[rows.length - 1] || null;
}

function deltaClass(delta) {
  if (delta < 0) return 'text-emerald-700';
  if (delta > 0) return 'text-red-700';
  return 'text-slate-600';
}

function formatDelta(delta) {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return 'No change';
  if (delta > 0) return `+${delta.toFixed(1)} pts higher`;
  if (delta < 0) return `${delta.toFixed(1)} pts lower`;
  return 'No change';
}

export default function Insights() {
  const { dashboard, profile, insightSimulation, setInsightSimulation } = useStore();
  const topChange = dashboard?.bio_age?.contributing_factors?.[0];
  const simulation = insightSimulation?.simulation;
  const simulationDuration = simulation?.duration?.label || '6 months';
  const simulatedTenYear = findYear(simulation?.new_risk_projections, 10);
  const currentTenYear = findYear(dashboard?.risk_projections, 10);
  const scenarioSleep = insightSimulation?.changes?.sleep;
  const currentSleep = profile?.sleep_hours;
  const riskComparisons = currentTenYear && simulatedTenYear ? [
    {
      label: '10-year diabetes risk',
      current: (currentTenYear.diabetes_risk || 0) * 100,
      projected: (simulatedTenYear.diabetes_risk || 0) * 100
    },
    {
      label: '10-year heart risk',
      current: (currentTenYear.cvd_risk || 0) * 100,
      projected: (simulatedTenYear.cvd_risk || 0) * 100
    },
    {
      label: '10-year metabolic risk',
      current: (currentTenYear.metabolic_risk || 0) * 100,
      projected: (simulatedTenYear.metabolic_risk || 0) * 100
    },
    {
      label: '10-year mental decline risk',
      current: (currentTenYear.mental_decline_risk || 0) * 100,
      projected: (simulatedTenYear.mental_decline_risk || 0) * 100
    }
  ] : [];
  const topRiskShift = riskComparisons.length
    ? [...riskComparisons].sort((a, b) => Math.abs(b.projected - b.current) - Math.abs(a.projected - a.current))[0]
    : null;
  const changedInputs = [
    scenarioSleep !== undefined && currentSleep !== undefined
      ? `sleep from ${currentSleep}h to ${scenarioSleep}h`
      : null,
    insightSimulation?.changes?.exercise !== undefined && profile?.exercise_hours_week !== undefined
      ? `exercise from ${profile.exercise_hours_week} to ${insightSimulation.changes.exercise} h/week`
      : null,
    insightSimulation?.changes?.stress !== undefined && profile?.stress_level !== undefined
      ? `stress from ${profile.stress_level}/10 to ${insightSimulation.changes.stress}/10`
      : null,
    insightSimulation?.changes?.screen_time !== undefined && profile?.screen_time_hours !== undefined
      ? `screen time from ${profile.screen_time_hours}h to ${insightSimulation.changes.screen_time}h`
      : null,
    insightSimulation?.changes?.duration
      ? `holding the scenario for ${simulationDuration.toLowerCase()}`
      : null,
  ].filter(Boolean);
  const nextStepText = simulation
    ? simulation.improvement >= 0
      ? `This scenario is worth taking seriously because it improves biological age. The next check is whether ${topRiskShift?.label || 'your highest risk'} drops enough to make this a habit you keep.`
      : `This scenario is not buying you enough. It mainly hurts ${topRiskShift?.label || 'your projected risk'}, so the smarter next test is to undo the most damaging change first${scenarioSleep !== undefined ? `, especially the drop to ${scenarioSleep}h sleep` : ''}.`
    : topChange
      ? `Your highest-leverage move from the current profile is ${topChange.change.toLowerCase()}. Test that single habit first before stacking multiple changes.`
      : 'Use one slider at a time and watch which risk curve drops most clearly.';
  const checkpointText = topRiskShift
    ? `For your current profile, Year 10 matters most because ${topRiskShift.label} is where the baseline and scenario separate most clearly.`
    : 'Year 10 is usually the clearest summary because it shows the trend without exaggerating distant tail risk.';
  const readHint = simulation
    ? `You tested ${changedInputs.join(', ') || 'a hypothetical change'}. If the dashed scenario line sits above the filled baseline, that change is making the outlook worse.`
    : 'Higher curves mean higher cumulative risk over time. Focus on the metric that looks most elevated for your current profile.';

  return (
    <div className="space-y-6">
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6 border-l-4 border-l-emerald-500 text-sm text-slate-600 italic leading-relaxed">
        {dashboard?.narrative || 'Complete your profile to get a personalized health narrative.'}
      </div>
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">One Change You Should Do Today</div>
        {topChange ? (
          <>
            <div className="text-2xl font-semibold text-slate-900 mt-2">{topChange.change}</div>
            <div className="text-sm text-slate-600 mt-2">
              Estimated biological age reduction if you make this your next consistent habit:
              {' '}
              <span className="font-semibold text-emerald-700">
                {topChange.estimated_bio_age_reduction?.toFixed?.(1) ?? topChange.estimated_bio_age_reduction} years
              </span>
            </div>
          </>
        ) : (
          <div className="text-sm text-slate-500 mt-2">Add more profile data to rank your highest-impact next step.</div>
        )}
      </div>
      <HabitSliders />
      <RiskChart
        data={dashboard?.risk_projections || []}
        comparisonData={simulation?.new_risk_projections || []}
        title={simulation ? 'Risk Forecast: Current vs Your Last Scenario' : 'Risk Forecast From Your Current Profile'}
        subtitle={
          simulation
            ? 'The filled curve is your saved baseline. The dashed curve shows your latest slider simulation so you can see if the scenario genuinely improves your outlook.'
            : 'Pick a metric and read the 5, 10, and 15-year snapshots to understand where risk is heading from your current saved profile.'
        }
        nextStepText={nextStepText}
        checkpointText={checkpointText}
        readHint={readHint}
      />
      <WorkoutTargets data={dashboard?.workout_targets} />
      <div className={`fixed inset-y-0 right-0 w-[480px] max-w-[90vw] bg-slate-900 text-white shadow-2xl transform transition-transform duration-300 z-50 overflow-y-auto ${simulation ? 'translate-x-0 animate-slide-in' : 'translate-x-full pointer-events-none'}`}>
        {simulation ? (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-sm font-semibold uppercase tracking-wider text-slate-400">Simulation Panel</div>
                <div className="text-2xl font-bold text-white mt-1">Your Future in {simulationDuration}</div>
              </div>
              <div className="rounded-full bg-white/10 px-3 py-1 text-sm">
                {simulation.improvement >= 0 ? `▼ ${simulation.improvement.toFixed(1)} years younger` : `▲ ${Math.abs(simulation.improvement).toFixed(1)} years older`}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-400">Bio Age</div>
              <div className="text-3xl font-bold mt-1">{simulation.current.overall} → <span className={simulation.improvement >= 0 ? 'text-emerald-400' : 'text-red-400'}>{simulation.projected.overall}</span></div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="text-sm font-semibold text-white mb-3">Subsystem Changes</div>
              <div className="space-y-2 text-sm">
                {[
                  ['CV', simulation.current.cardiovascular, simulation.projected.cardiovascular],
                  ['Met', simulation.current.metabolic, simulation.projected.metabolic],
                  ['MSK', simulation.current.musculoskeletal, simulation.projected.musculoskeletal],
                  ['Neuro', simulation.current.neurological, simulation.projected.neurological],
                ].map(([label, current, projected]) => {
                  const delta = projected - current;
                  return <div key={label} className="flex items-center justify-between"><span className="text-slate-400">{label}</span><span>{current} → <span className={delta < 0 ? 'text-emerald-400' : delta > 0 ? 'text-red-400' : 'text-slate-400'}>{projected}</span></span></div>;
                })}
              </div>
            </div>
            {riskComparisons.length > 0 ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="text-sm font-semibold text-white mb-3">10-Year Risk Impact</div>
                <div className="space-y-2 text-sm">
                  {riskComparisons.map((item) => {
                    const delta = item.projected - item.current;
                    return <div key={item.label} className="flex items-center justify-between"><span className="text-slate-400">{item.label}</span><span>{item.current.toFixed(1)}% → <span className={delta < 0 ? 'text-emerald-400' : delta > 0 ? 'text-red-400' : 'text-slate-400'}>{item.projected.toFixed(1)}%</span></span></div>;
                  })}
                </div>
              </div>
            ) : null}
            {insightSimulation?.narrative ? <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm leading-relaxed text-slate-300">{insightSimulation.narrative}</div> : null}
            <button type="button" onClick={() => setInsightSimulation(null)} className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:text-white transition">✕ Close</button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
