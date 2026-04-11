import { Sparkles } from 'lucide-react';
import ChatInterface from '../components/ChatInterface';
import useStore from '../store';

export default function FutureSelf() {
  const { selectedUserId, profile, insightSimulation } = useStore();
  const simulationContext = insightSimulation?.simulation ? [
    'Latest Insights scenario (hypothetical, not saved profile):',
    `Sleep: ${insightSimulation?.changes?.sleep ?? 'unchanged'} hours`,
    `Exercise: ${insightSimulation?.changes?.exercise ?? 'unchanged'} hours/week`,
    `Diet score: ${insightSimulation?.changes?.diet ?? 'unchanged'} / 4`,
    `Stress level: ${insightSimulation?.changes?.stress ?? 'unchanged'} / 10`,
    `Screen time: ${insightSimulation?.changes?.screen_time ?? 'unchanged'} hours/day`,
    `Projected bio age: ${insightSimulation.simulation.projected.overall} (current ${insightSimulation.simulation.current.overall})`,
    `Improvement: ${insightSimulation.simulation.improvement} years`,
  ].join('\n') : '';

  return (
    <div>
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-red-950 p-8 text-white mb-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(239,68,68,0.15),transparent)]" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
              <Sparkles className="text-red-400" size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold">Your Future Self</h2>
              <p className="text-slate-400 text-sm">Age {(profile?.age || 19) + 15} — speaking from {new Date().getFullYear() + 15}</p>
            </div>
          </div>
          <p className="mt-4 text-slate-300 text-sm leading-relaxed max-w-2xl">
            This is you, 15 years from now. They lived through the consequences of your current habits and they are not going to sugarcoat it.
          </p>
        </div>
      </div>
      <ChatInterface
        chatType="future"
        userId={selectedUserId}
        title="Future Self"
        placeholder="Ask your future self what happens if you keep going like this..."
        helperText="This chat is for long-term health trajectory, risk, habit consequences, and where your current patterns may lead. Unrelated questions are blocked."
        suggestedPrompts={[
          'What happens to me if I keep living like this?',
          'What do you wish I had done at my age?',
          'Be honest — am I heading somewhere bad?',
          "What's the first thing I should fix right now?",
          'Tell me the truth about my health numbers.',
        ]}
        context={simulationContext}
        dark
        tall
      />
    </div>
  );
}
