import { BrainCircuit, Clock3, DatabaseZap, Flame, Music2, Sparkles, Workflow } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getResearchFeatures } from '../api';
import useStore from '../store';

const cardConfig = {
  react: { title: 'ReAct', icon: Workflow, accent: 'text-sky-700 bg-sky-50 border-sky-200' },
  daao: { title: 'DAAO', icon: BrainCircuit, accent: 'text-violet-700 bg-violet-50 border-violet-200' },
  semantic_cache: { title: 'Semantic Cache', icon: DatabaseZap, accent: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  reflexion: { title: 'Reflexion', icon: Sparkles, accent: 'text-amber-700 bg-amber-50 border-amber-200' },
  music_emotion: { title: 'Music Emotion', icon: Music2, accent: 'text-rose-700 bg-rose-50 border-rose-200' },
};

function formatDateTime(value) {
  if (!value) return 'Not used yet';
  // SQLite CURRENT_TIMESTAMP stores UTC. Append 'Z' so JS Date knows it's UTC
  // and converts to the user's local timezone automatically.
  let normalized = value;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(normalized)) {
    normalized = normalized.replace(' ', 'T') + 'Z';
  } else if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(normalized)) {
    normalized += 'Z';
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function EvidenceBlock({ title, children }) {
  return (
    <div className="glass-subcard px-4 py-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function ReactEvidence({ data }) {
  const runs = data?.recent_runs || [];
  return (
    <div className="space-y-3">
      {runs.length ? runs.map((run, index) => (
        <div key={`${run.timestamp}-${index}`} className="glass-subcard px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">{run.agent_label}</div>
              <div className="text-xs text-slate-500 mt-1">{formatDateTime(run.timestamp)} • {run.difficulty} • {run.step_count} steps</div>
            </div>
          </div>
          {run.trace_preview?.length ? (
            <div className="mt-3 space-y-2">
              {run.trace_preview.map((step, stepIndex) => (
                <div key={`${step.timestamp || stepIndex}-${stepIndex}`} className={`rounded-xl px-3 py-2 text-xs ${
                  step.type === 'thought'
                    ? 'bg-amber-50 text-amber-800'
                    : step.type === 'action'
                      ? 'bg-sky-50 text-sky-800'
                      : 'bg-emerald-50 text-emerald-800'
                }`}>
                  <span className="font-semibold capitalize">{step.type}:</span> {step.content}
                </div>
              ))}
            </div>
          ) : null}
          {run.answer_preview ? <div className="mt-3 text-sm text-slate-600">{run.answer_preview}</div> : null}
        </div>
      )) : <div className="empty-state-card px-4 py-4 text-sm text-slate-500">No completed ReAct traces yet. Ask Coach, Mental Health, or Future Self a question to generate one.</div>}
    </div>
  );
}

function DAAOEvidence({ data }) {
  const counts = data?.difficulty_counts || {};
  const rows = data?.recent_classifications || [];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        {['easy', 'medium', 'hard'].map((level) => (
          <div key={level} className="glass-subcard px-4 py-4 text-center">
            <div className="text-xs uppercase tracking-wide text-slate-500">{level}</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900">{counts[level] || 0}</div>
          </div>
        ))}
      </div>
      {rows.length ? rows.map((row, index) => (
        <div key={`${row.timestamp}-${index}`} className="glass-subcard px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-900">{row.agent_label}</div>
            <div className="text-xs text-slate-500 mt-1">{formatDateTime(row.timestamp)}</div>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold text-slate-800 capitalize">{row.difficulty}</div>
            <div className="text-xs text-slate-500">max {row.max_iterations} iterations</div>
          </div>
        </div>
      )) : <div className="empty-state-card px-4 py-4 text-sm text-slate-500">No difficulty classifications recorded yet.</div>}
    </div>
  );
}

function CacheEvidence({ data }) {
  const hits = data?.recent_hits || [];
  return hits.length ? (
    <div className="space-y-3">
      {hits.map((hit, index) => (
        <div key={`${hit.timestamp}-${index}`} className="glass-subcard px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">{hit.agent_label}</div>
              <div className="text-xs text-slate-500 mt-1">{formatDateTime(hit.timestamp)} • {hit.difficulty}</div>
            </div>
            <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">cache hit</div>
          </div>
          <div className="mt-3 text-sm text-slate-600">{hit.response_preview}</div>
        </div>
      ))}
    </div>
  ) : (
    <div className="empty-state-card px-4 py-4 text-sm text-slate-500">No semantic cache hits yet. They appear when a new question closely matches an earlier one under the same health-state fingerprint.</div>
  );
}

function ReflectionEvidence({ data }) {
  const rows = data?.recent_reflections || [];
  return rows.length ? (
    <div className="space-y-3">
      {rows.map((row, index) => (
        <div key={`${row.created_at}-${index}`} className="glass-subcard px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">{row.agent_label}</div>
              <div className="text-xs text-slate-500 mt-1">{formatDateTime(row.created_at)}</div>
            </div>
            <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${row.is_active ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
              {row.is_active ? 'active' : 'archived'}
            </div>
          </div>
          {row.query_summary ? <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Trigger</div> : null}
          {row.query_summary ? <div className="mt-1 text-sm text-slate-600">{row.query_summary}</div> : null}
          <div className="mt-3 text-sm text-slate-700">{row.reflection}</div>
        </div>
      ))}
    </div>
  ) : (
    <div className="empty-state-card px-4 py-4 text-sm text-slate-500">No Reflexion memories stored yet. Medium and hard runs generate them after the answer completes.</div>
  );
}

function MusicEvidence({ data }) {
  const tracks = data?.recent_tracks || [];
  const syncs = data?.recent_syncs || [];
  return (
    <div className="space-y-3">
      {data?.latest_sync ? (
        <div className="glass-subcard px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">{data.latest_sync.emotion_class?.label || 'Latest Spotify mood'}</div>
              <div className="text-xs text-slate-500 mt-1">{formatDateTime(data.latest_sync.timestamp)} • {data.latest_sync.track_count} tracks</div>
            </div>
            <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${data.latest_sync.flagged ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
              {data.latest_sync.flagged ? 'flagged' : 'stable'}
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
            <div><div className="text-slate-500">Valence</div><div className="mt-1 font-semibold text-slate-900">{data.latest_sync.avg_valence}</div></div>
            <div><div className="text-slate-500">Energy</div><div className="mt-1 font-semibold text-slate-900">{data.latest_sync.avg_energy}</div></div>
            <div><div className="text-slate-500">Danceability</div><div className="mt-1 font-semibold text-slate-900">{data.latest_sync.avg_danceability}</div></div>
          </div>
        </div>
      ) : null}
      <div className="grid gap-3 xl:grid-cols-2">
        <EvidenceBlock title="Recent Syncs">
          {syncs.length ? (
            <div className="space-y-3">
              {syncs.map((row, index) => (
                <div key={`${row.timestamp}-${index}`} className="rounded-xl border border-slate-200/70 bg-white/70 px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-slate-900">{row.emotion_class?.label || 'Mood snapshot'}</div>
                    <div className="text-xs text-slate-500">{row.track_count} tracks</div>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">{formatDateTime(row.timestamp)}</div>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-slate-500">No Spotify sync snapshots yet.</div>}
        </EvidenceBlock>
        <EvidenceBlock title="Track Proof">
          {tracks.length ? (
            <div className="space-y-3">
              {tracks.map((track, index) => (
                <div key={`${track.played_at}-${index}`} className="rounded-xl border border-slate-200/70 bg-white/70 px-3 py-3 flex items-center gap-3">
                  {track.album_image_url ? <img src={track.album_image_url} alt={track.album_name || track.track_name || 'Album art'} className="h-12 w-12 rounded-xl object-cover border border-slate-200/70" /> : <div className="h-12 w-12 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500">♪</div>}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-slate-900">{track.track_name || 'Unknown track'}</div>
                    <div className="truncate text-xs text-slate-500 mt-1">{track.artist_names || 'Unknown artist'}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{formatDateTime(track.played_at)}</div>
                  </div>
                  {track.spotify_url ? <a href={track.spotify_url} target="_blank" rel="noreferrer" className="text-xs font-medium text-emerald-700">Open</a> : null}
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-slate-500">No saved Spotify tracks yet.</div>}
        </EvidenceBlock>
      </div>
    </div>
  );
}

export default function ResearchLab() {
  const { selectedUserId, profile, showToast } = useStore();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedUserId) return;
    (async () => {
      try {
        setLoading(true);
        const response = await getResearchFeatures(selectedUserId);
        setData(response.data);
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedUserId, showToast]);

  const cards = useMemo(() => Object.entries(data?.features || {}), [data]);

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 px-6 py-8 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.18),transparent_26%),radial-gradient(circle_at_bottom_left,rgba(16,185,129,0.18),transparent_30%)]" />
        <div className="relative">
          <div className="text-xs uppercase tracking-[0.24em] text-emerald-200/80">Research Lab</div>
          <div className="mt-3 text-3xl font-semibold tracking-tight">See the paper-backed systems working on your profile.</div>
          <div className="mt-3 max-w-3xl text-sm text-slate-300 md:text-base">
            This page does not describe the features abstractly. It shows the live evidence: traces, routing decisions, cache reuse, stored reflections, and Spotify emotion outputs tied to {profile?.name || selectedUserId}.
          </div>
          <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs text-slate-200">
            <Clock3 size={13} />
            Generated {formatDateTime(data?.generated_at)}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => <div key={index} className="glass-card h-56 animate-pulse bg-slate-200/60" />)}
        </div>
      ) : null}

      {!loading && !cards.length ? (
        <div className="glass-card p-8 text-sm text-slate-500">No research-feature evidence is available yet for this profile.</div>
      ) : null}

      {!loading ? (
        <div className="grid gap-6">
          {cards.map(([key, feature]) => {
            const config = cardConfig[key] || { title: feature.name, icon: Flame, accent: 'text-slate-700 bg-slate-50 border-slate-200' };
            const Icon = config.icon;
            return (
              <section key={key} className="glass-card p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide ${config.accent}`}>
                      <Icon size={14} />
                      {config.title}
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-slate-900">{feature.paper_label}</div>
                    <div className="mt-2 max-w-3xl text-sm text-slate-600">{feature.how_used}</div>
                  </div>
                  <div className="glass-subcard min-w-[230px] px-4 py-4">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Last used</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{formatDateTime(feature.last_used_at)}</div>
                    <div className="mt-3 text-xs uppercase tracking-wide text-slate-500">Visible in</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(feature.where_used || []).map((item) => <span key={item} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{item}</span>)}
                    </div>
                  </div>
                </div>

                <div className="mt-6 max-h-[480px] overflow-y-auto pr-1">
                  {key === 'react' ? <ReactEvidence data={feature} /> : null}
                  {key === 'daao' ? <DAAOEvidence data={feature} /> : null}
                  {key === 'semantic_cache' ? <CacheEvidence data={feature} /> : null}
                  {key === 'reflexion' ? <ReflectionEvidence data={feature} /> : null}
                  {key === 'music_emotion' ? <MusicEvidence data={feature} /> : null}
                </div>
              </section>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
