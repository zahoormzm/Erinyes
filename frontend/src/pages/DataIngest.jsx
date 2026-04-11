import { Camera, Clock3, FileText, Image, Smartphone } from 'lucide-react';
import { useEffect, useState } from 'react';
import FileUpload from '../components/FileUpload';
import ManualEntryForm from '../components/ManualEntryForm';
import PHQ9CalibrationCard from '../components/PHQ9CalibrationCard';
import useStore from '../store';
import { getDashboard, getDataFreshness, uploadAppleHealth, uploadFaceAge, uploadFile } from '../api';

const sources = [
  { key: 'blood_pdf', label: 'Blood Report', icon: FileText, accept: '.pdf' },
  { key: 'cultfit_image', label: 'Cult.fit Report', icon: Image, accept: '.png,.jpg,.jpeg' },
  { key: 'apple_health_xml', label: 'Apple Health', icon: Smartphone, accept: '.xml,.zip' },
  { key: 'face_age', label: 'Face Age Selfie', icon: Camera, accept: '.jpg,.jpeg,.png' }
];

export default function DataIngest() {
  const { selectedUserId, showToast, setDashboard, setProfile } = useStore();
  const [selected, setSelected] = useState(sources[0]);
  const [result, setResult] = useState(null);
  const [freshness, setFreshness] = useState([]);
  const [formRefreshKey, setFormRefreshKey] = useState(0);
  const extracted = result?.extracted;
  const uploadAppliedFields = result?.profile_updates_applied || result?.extracted?.recognized_fields || {};
  const uploadIgnoredFields = result?.ignored_metrics || {};
  const mobileSyncRows = freshness.filter((item) => ['healthkit', 'apple_health', 'manual_mobile'].includes(item.source));
  const sortedMobileSyncRows = [...mobileSyncRows].sort((left, right) => {
    const leftTime = left.last_synced ? new Date(String(left.last_synced).replace(' ', 'T')).getTime() : 0;
    const rightTime = right.last_synced ? new Date(String(right.last_synced).replace(' ', 'T')).getTime() : 0;
    return rightTime - leftTime;
  });

  const formatDateTime = (value) => {
    if (!value) return 'Not uploaded yet';
    const normalizedValue = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
      ? value.replace(' ', 'T') + 'Z'
      : value;
    const parsed = new Date(normalizedValue);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  };

  const formatDayLabel = (value) => {
    if (!value) return 'No sync yet';
    const normalizedValue = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
      ? value.replace(' ', 'T') + 'Z'
      : value;
    const parsed = new Date(normalizedValue);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  };

  const loadFreshness = async () => {
    try {
      const response = await getDataFreshness(selectedUserId);
      setFreshness(response.data || []);
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  useEffect(() => {
    loadFreshness();
  }, [selectedUserId]);

  const endpoint = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', selectedUserId);
    if (selected.key === 'face_age') return uploadFaceAge(formData);
    if (selected.key === 'apple_health_xml') return uploadAppleHealth(formData);
    formData.append('data_type', selected.key);
    return uploadFile(formData);
  };

  const handleUploadResult = async (payload) => {
    setResult(payload);
    if (payload?.profile) {
      setProfile(payload.profile);
    }
    try {
      const dashboardResponse = await getDashboard(selectedUserId);
      setDashboard(dashboardResponse.data);
    } catch (error) {
      showToast(error.message, 'error');
    }
    setFormRefreshKey((current) => current + 1);
    await loadFreshness();
  };

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {sources.map((source) => {
          const Icon = source.icon;
          return (
            <button key={source.key} onClick={() => setSelected(source)} className={`glass-card glass-card-hover p-4 text-left ${selected.key === source.key ? 'ring-2 ring-emerald-500 bg-emerald-50/90' : 'cursor-pointer hover:border-slate-300'}`}>
              <Icon size={20} className="text-slate-600" />
              <div className="font-medium text-slate-700 mt-3">{source.label}</div>
            </button>
          );
        })}
      </div>
      <FileUpload accept={selected.accept} label={selected.label} endpoint={endpoint} onUpload={handleUploadResult} />
      <PHQ9CalibrationCard
        className="mt-6"
        title="Mental Baseline Calibration"
        description="Use this once to set a real PHQ-9 baseline for the profile. That saved score remains active until you recalibrate it again, and it now appears in this ingestion timeline like any other data source."
        onCalibrated={loadFreshness}
      />
      {result && (
        <div className="glass-card mt-6 p-6">
          <div className="text-sm font-semibold text-slate-900">This Upload Changed</div>
          <div className="text-sm text-slate-500 mt-1">
            This section only summarizes the current upload. The larger freshness section below is your overall profile timeline across all sources.
          </div>
          {selected.key === 'apple_health_xml' && (
            <div className="mt-4 space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xs rounded-full bg-blue-50 text-blue-700 px-2 py-1">{Object.keys(uploadAppliedFields).length} profile fields applied</span>
                <span className="text-xs rounded-full bg-emerald-50 text-emerald-700 px-2 py-1">{result.workouts_found || 0} workouts imported</span>
                <span className="text-xs rounded-full bg-slate-100 text-slate-700 px-2 py-1">{(result.metrics_detected || []).length} metrics detected</span>
              </div>
              {!!Object.keys(uploadAppliedFields).length && (
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Applied To Profile</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                    {Object.entries(uploadAppliedFields).map(([key, value]) => (
                      <div key={key} className="glass-subcard px-3 py-2">
                        <div className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</div>
                        <div className="text-sm font-medium text-slate-800 mt-1">{value ?? 'Not provided'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {!!Object.keys(uploadIgnoredFields).length && (
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Detected But Not Stored As Profile Fields</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                    {Object.entries(uploadIgnoredFields).map(([key, value]) => (
                      <div key={key} className="glass-subcard px-3 py-2">
                        <div className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</div>
                        <div className="text-sm font-medium text-slate-800 mt-1">{value ?? 'Not provided'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {!Object.keys(uploadAppliedFields).length && (
                <div className="text-sm text-amber-700">
                  The upload succeeded, but no Apple Health metrics from this file were suitable to apply directly to the profile.
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <div className="glass-card mt-6 p-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-slate-100 flex items-center justify-center">
            <Clock3 size={18} className="text-slate-600" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Overall Profile Freshness And Refresh Windows</div>
            <div className="text-sm text-slate-500">
              This is your full source timeline for the selected user, across all uploads and syncs, not just the latest file.
            </div>
          </div>
        </div>
        {!!mobileSyncRows.length && (
          <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center gap-2">
              <Smartphone size={16} className="text-blue-700" />
              <div className="text-sm font-semibold text-blue-900">iPhone / Apple Sync Activity</div>
            </div>
            <div className="text-sm text-blue-800 mt-1">
              If the iPhone app or Apple Health import synced successfully, it will appear here immediately.
            </div>
            <div className="grid gap-3 md:grid-cols-3 mt-4">
              {sortedMobileSyncRows.map((item) => (
                <div key={`mobile-${item.source}`} className="rounded-2xl border border-blue-200 bg-white/80 px-3 py-3 backdrop-blur-sm">
                  <div className="text-xs uppercase tracking-wide text-slate-500">{item.label}</div>
                  <div className="text-sm font-medium text-slate-900 mt-1">{formatDateTime(item.last_synced)}</div>
                  <div className="text-xs text-slate-500 mt-2">
                    {item.days_since_upload == null ? 'No sync yet' : `${item.days_since_upload} days since last sync`}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">Refresh window: every {item.recommended_interval_days} days</div>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-2xl border border-dashed border-blue-200 bg-white/70 px-4 py-4 backdrop-blur-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Phone Timeline</div>
              <div className="mt-3 space-y-3">
                {sortedMobileSyncRows.map((item) => (
                  <div key={`timeline-${item.source}`} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="mt-1 h-2.5 w-2.5 rounded-full bg-blue-500" />
                      <div className="mt-1 h-full min-h-6 w-px bg-blue-200 last:hidden" />
                    </div>
                    <div className="pb-2">
                      <div className="text-sm font-medium text-slate-900">{item.label}</div>
                      <div className="text-xs text-slate-500 mt-1">{formatDayLabel(item.last_synced)} · Synced on {formatDateTime(item.last_synced)}</div>
                      <div className="text-xs text-slate-500 mt-1">
                        {item.days_since_upload == null ? 'Waiting for first sync' : `${item.days_since_upload} days since this source last updated your profile.`}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="mt-5 grid gap-3">
          {freshness.map((item) => {
            const urgencyClass = item.urgency === 'high'
              ? 'border-red-200 bg-red-50'
              : item.urgency === 'medium'
                ? 'border-amber-200 bg-amber-50'
                : 'border-slate-200 bg-slate-50';
            return (
              <div key={`${item.type}-${item.source}`} className={`rounded-xl border p-4 ${urgencyClass}`}>
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{item.label}</div>
                    <div className="text-sm text-slate-600 mt-1">{item.message}</div>
                  </div>
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {String(item.status || item.type).replaceAll('_', ' ')}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mt-4">
                  <div className="rounded-lg bg-white/80 px-3 py-2">
                    <div className="text-[11px] uppercase tracking-wide text-slate-500">Last Recorded</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">{formatDateTime(item.last_synced)}</div>
                  </div>
                  <div className="rounded-lg bg-white/80 px-3 py-2">
                    <div className="text-[11px] uppercase tracking-wide text-slate-500">Recommended Refresh</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">Every {item.recommended_interval_days} days</div>
                  </div>
                  <div className="rounded-lg bg-white/80 px-3 py-2">
                    <div className="text-[11px] uppercase tracking-wide text-slate-500">Days Since</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">
                      {item.days_since_upload == null ? 'No upload yet' : `${item.days_since_upload} days`}
                    </div>
                  </div>
                  <div className="rounded-lg bg-white/80 px-3 py-2">
                    <div className="text-[11px] uppercase tracking-wide text-slate-500">Next Due</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">
                      {item.next_due_at ? formatDateTime(item.next_due_at) : 'Upload needed'}
                    </div>
                    {item.days_overdue > 0 && (
                      <div className="text-xs text-red-600 mt-1">Overdue by {item.days_overdue} days</div>
                    )}
                    {!item.days_overdue && item.days_until_due != null && (
                      <div className="text-xs text-slate-500 mt-1">Due in about {item.days_until_due} days</div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {selected.key === 'blood_pdf' && extracted?.source_summary && (
          <div className="glass-card mt-6 p-6">
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-sm font-semibold text-slate-800">Flexible Lab Extraction</div>
            <span className="text-xs rounded-full bg-emerald-50 text-emerald-700 px-2 py-1">{extracted.source_summary.tests_found} tests found</span>
            <span className="text-xs rounded-full bg-blue-50 text-blue-700 px-2 py-1">{extracted.source_summary.recognized_count} recognized</span>
            <span className="text-xs rounded-full bg-amber-50 text-amber-700 px-2 py-1">{extracted.source_summary.unmapped_count} unmapped</span>
            {!!extracted.source_summary.ambiguous_count && <span className="text-xs rounded-full bg-orange-50 text-orange-700 px-2 py-1">{extracted.source_summary.ambiguous_count} review needed</span>}
            {!!extracted.source_summary.invalid_count && <span className="text-xs rounded-full bg-red-50 text-red-700 px-2 py-1">{extracted.source_summary.invalid_count} rejected</span>}
          </div>
          {!!Object.keys(extracted.recognized_fields || {}).length && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Profile Updates Applied</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                {Object.entries(extracted.recognized_fields).map(([key, value]) => (
                  <div key={key} className="glass-subcard px-3 py-2">
                    <div className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">{value ?? 'Not provided'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!!extracted.unmapped_tests?.length && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Additional Tests Kept For Review</div>
              <div className="mt-2 text-sm text-slate-600">
                {extracted.unmapped_tests.map((item) => item.name).join(', ')}
              </div>
            </div>
          )}
          {!!extracted.ambiguous_tests?.length && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Metrics Not Auto-Applied Because Multiple Conflicting Values Were Detected</div>
              <div className="mt-2 space-y-2">
                {extracted.ambiguous_tests.map((item) => (
                  <div key={item.metric} className="rounded-lg bg-orange-50 border border-orange-200 px-3 py-2">
                    <div className="text-sm font-medium text-orange-900">{item.label}</div>
                    <div className="text-xs text-orange-800 mt-1">
                      Candidates: {item.candidates.map((candidate) => candidate.value).join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!!extracted.invalid_tests?.length && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Rejected Values That Were Out Of Plausible Range</div>
              <div className="mt-2 space-y-2">
                {extracted.invalid_tests.map((item, index) => (
                  <div key={`${item.metric || item.name}-${index}`} className="rounded-lg bg-red-50 border border-red-200 px-3 py-2">
                    <div className="text-sm font-medium text-red-900">{item.name}</div>
                    <div className="text-xs text-red-800 mt-1">
                      Value {item.value} was ignored because it looked invalid for {item.metric?.replaceAll('_', ' ') || item.name}.
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!!extracted.missing_common_tests?.length && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Common Tests Not Present In This Report</div>
              <div className="mt-2 text-sm text-slate-600">
                {extracted.missing_common_tests.join(', ')}
              </div>
            </div>
          )}
        </div>
      )}
      {selected.key === 'cultfit_image' && result && (
        <div className="glass-card mt-6 p-6">
          <div className="text-sm font-semibold text-slate-800">Cult.fit Extraction</div>
          {!!Object.keys(result.extracted || {}).length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
              {Object.entries(result.extracted || {}).map(([key, value]) => (
                <div key={key} className="glass-subcard px-3 py-2">
                  <div className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</div>
                  <div className="text-sm font-medium text-slate-800 mt-1">{value ?? 'Not extracted'}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-amber-700 mt-3">
              The report upload completed, but no body-composition values were extracted from this image.
            </div>
          )}
        </div>
      )}
      {result && (
        <details className="glass-card mt-6 p-6">
          <summary className="cursor-pointer text-sm font-semibold text-slate-800">Raw Upload Response</summary>
          <pre className="text-xs text-slate-700 whitespace-pre-wrap mt-4">{JSON.stringify(result, null, 2)}</pre>
        </details>
      )}
      <div className="border-t border-slate-200 my-8" />
      <ManualEntryForm refreshKey={formRefreshKey} />
    </div>
  );
}
