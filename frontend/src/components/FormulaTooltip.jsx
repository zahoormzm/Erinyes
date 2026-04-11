import { Calculator } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { getFormulaBreakdown } from '../api';

export default function FormulaTooltip({ userId, metric, children }) {
  const [show, setShow] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [position, setPosition] = useState('top');
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!show || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setPosition(rect.top < 220 ? 'bottom' : 'top');
  }, [show]);

  const fetchBreakdown = async () => {
    if (data || !userId || !metric) return;
    setLoading(true);
    try {
      const response = await getFormulaBreakdown(userId, metric);
      setData(response.data);
    } catch {
      // ignore tooltip fetch failures
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={() => {
        setShow(true);
        fetchBreakdown();
      }}
      onMouseLeave={() => setShow(false)}
    >
      <div className="cursor-help border-b border-dashed border-slate-300">
        {children}
      </div>
      {show ? (
        <div
          className={`absolute z-50 left-1/2 -translate-x-1/2 w-80 max-w-[calc(100vw-1rem)] bg-slate-900 text-white rounded-2xl shadow-2xl p-4 text-xs animate-fade-in pointer-events-none ${position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`}
        >
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold mb-2">
            <Calculator size={12} />
            How this is calculated
          </div>
          {loading ? <div className="text-slate-400">Loading...</div> : null}
          {!loading && data ? (
            <>
              <div className="text-slate-300 font-mono text-[11px] mb-2">{data.formula}</div>
              {data.inputs ? Object.entries(data.inputs).map(([key, val]) => {
                if (typeof val === 'object' && val?.components) {
                  return (
                    <div key={key}>
                      {val.components.map((component, index) => (
                        <div key={`${key}-${index}`} className="flex justify-between gap-2 py-0.5 border-b border-slate-800">
                          <span className="text-slate-400">{component.input}: {component.value}</span>
                          <span className={component.delta > 0 ? 'text-red-400' : component.delta < 0 ? 'text-emerald-400' : 'text-slate-500'}>
                            {component.delta > 0 ? '+' : ''}{component.delta}
                            {metric === 'mental_wellness_score' || metric.endsWith('_penalty') ? ' pts' : 'yr'}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                }
                return null;
              }) : null}
              {data.sources?.length ? <div className="mt-2 text-slate-500 italic">Sources: {data.sources.join(', ')}</div> : null}
            </>
          ) : null}
          <div className={`absolute left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-r-[6px] border-transparent ${position === 'top' ? 'top-full border-t-[6px] border-t-slate-900' : 'bottom-full border-b-[6px] border-b-slate-900'}`} />
        </div>
      ) : null}
    </div>
  );
}
