import FormulaTooltip from './FormulaTooltip';
import useStore from '../store';

export default function AgeComparison({ data, compact = false }) {
  const { dashboard } = useStore();
  const source = data || dashboard;
  if (!source) {
    return <div className={`glass-card ${compact ? 'p-4 h-[250px]' : 'p-6 h-[360px]'} animate-pulse bg-slate-200/70`} />;
  }
  const chrono = source.profile?.age || 0;
  const bioAge = source.bio_age_overall || source.bio_age?.overall || 0;
  const faceAge = source.face_age || 0;
  const maxVal = Math.max(chrono + 10, bioAge + 10, faceAge + 10, 1);
  const bars = [
    { label: 'Chronological', value: chrono, className: 'bg-slate-400' },
    { label: 'Biological', value: bioAge, className: bioAge < chrono ? 'bg-emerald-500' : 'bg-red-500' },
    { label: 'Face Age', value: faceAge, className: 'bg-blue-500', display: faceAge ? faceAge.toFixed(1) : '---' }
  ];
  const diff = (chrono - bioAge).toFixed(1);

  return (
    <div className={`bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm hover:shadow-md transition-shadow ${compact ? 'p-4' : 'p-6'}`}>
      <div className={`flex items-end justify-center ${compact ? 'gap-4 h-[170px]' : 'gap-8 h-[280px]'}`}>
        {bars.map((bar) => (
          <div key={bar.label} className="flex flex-col items-center justify-end h-full">
            <div className={`${compact ? 'w-10' : 'w-16'} rounded-t-lg ${bar.className}`} style={{ height: `${(bar.value / maxVal) * 100}%` }} />
            {bar.label === 'Biological' ? (
              <FormulaTooltip userId={source.profile?.id || source.profile?.user_id} metric="bio_age_overall">
                <div className={`font-medium ${compact ? 'text-base mt-2' : 'text-lg mt-3'} text-slate-900`}>{bar.display || bar.value?.toFixed?.(1) || bar.value}</div>
              </FormulaTooltip>
            ) : (
              <div className={`font-medium ${compact ? 'text-base mt-2' : 'text-lg mt-3'} text-slate-900`}>{bar.display || bar.value?.toFixed?.(1) || bar.value}</div>
            )}
            <div className="text-xs text-slate-500 mt-1">{bar.label}</div>
          </div>
        ))}
      </div>
      <p className={`mt-3 ${compact ? 'text-xs' : 'text-sm'} font-medium ${bioAge < chrono ? 'text-emerald-600' : 'text-red-600'}`}>
        {bioAge < chrono ? `You are ${diff} years younger biologically` : `You are ${(bioAge - chrono).toFixed(1)} years older biologically`}
      </p>
    </div>
  );
}
