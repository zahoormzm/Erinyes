import { useEffect, useMemo, useState } from 'react';
import { clearReflections, createUser, deleteUser, getDataFreshness, getMobileHealth, getMobileProfile, getReflections, getServerInfo, getSpotifyStatus, getSpotifySync, getUsers, updateProfile } from '../api';
import useStore from '../store';

const demoUserNotes = {
  zahoor: 'Primary demo profile with broader health history, reminders, and multi-feature coverage for the main dashboard walkthrough.',
  riya: 'Secondary demo user suited for family-group and comparative views with a different baseline profile.',
  arjun: 'Third demo user for leaderboard, switching, and additional independent testing without affecting the main demo path.'
};

export default function Settings() {
  const { selectedUserId, profile, users, setProfile, setSelectedUser, setUsers, showToast } = useStore();
  const [server, setServer] = useState({ ip: 'localhost', port: '8000' });
  const [serverInfo, setServerInfo] = useState({ hostname: null, localhost_url: null, local_ips: [], mobile_base_urls: [] });
  const [spotifyStatus, setSpotifyStatus] = useState({ connected: false, connected_at: null, latest_sync: null, sync_history: [], recent_tracks: [] });
  const [mobileHealth, setMobileHealth] = useState({ status: 'unknown', server: null, version: null, timestamp: null });
  const [mobileProfile, setMobileProfile] = useState(null);
  const [mobileFreshness, setMobileFreshness] = useState([]);
  const [contacts, setContacts] = useState({
    doctor_name: profile?.doctor_name || '',
    doctor_email: profile?.doctor_email || '',
    doctor_phone: profile?.doctor_phone || '',
    emergency_contact_name: profile?.emergency_contact_name || '',
    emergency_contact_phone: profile?.emergency_contact_phone || '',
    privacy_level: 'summary'
  });
  const [newUser, setNewUser] = useState({ id: '', name: '', age: '', sex: 'female', height_cm: '' });
  const [locationForm, setLocationForm] = useState({
    location_label: profile?.location_label || '',
    latitude: profile?.latitude ?? '',
    longitude: profile?.longitude ?? '',
  });
  const [locating, setLocating] = useState(false);
  const [reflections, setReflections] = useState([]);
  const [showReflectionModal, setShowReflectionModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) || { id: selectedUserId, name: profile?.name || selectedUserId },
    [users, selectedUserId, profile]
  );
  const mobileBaseUrl = `http://${server.ip || 'localhost'}:${server.port || '8000'}`;
  const mobileDataRows = useMemo(
    () => mobileFreshness.filter((item) => ['healthkit', 'apple_health', 'manual_mobile'].includes(item.source)),
    [mobileFreshness]
  );

  const formatDateTime = (value) => {
    if (!value) return 'Not synced yet';
    const normalizedValue = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
      ? value.replace(' ', 'T') + 'Z'
      : value;
    const parsed = new Date(normalizedValue);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  };

  useEffect(() => {
    setContacts((previous) => ({
      ...previous,
      doctor_name: profile?.doctor_name || '',
      doctor_email: profile?.doctor_email || '',
      doctor_phone: profile?.doctor_phone || '',
      emergency_contact_name: profile?.emergency_contact_name || '',
      emergency_contact_phone: profile?.emergency_contact_phone || ''
    }));
    setLocationForm({
      location_label: profile?.location_label || '',
      latitude: profile?.latitude ?? '',
      longitude: profile?.longitude ?? '',
    });
  }, [profile]);

  useEffect(() => {
    if (!selectedUserId) return;
    (async () => {
      try {
        const [spotifyResponse, mobileProfileResponse, mobileFreshnessResponse] = await Promise.all([
          getSpotifyStatus(selectedUserId),
          getMobileProfile(selectedUserId),
          getDataFreshness(selectedUserId),
        ]);
        setSpotifyStatus(spotifyResponse.data);
        setMobileProfile(mobileProfileResponse.data);
        setMobileFreshness(mobileFreshnessResponse.data || []);
      } catch {
        setSpotifyStatus({ connected: false, connected_at: null, latest_sync: null, sync_history: [], recent_tracks: [] });
        setMobileProfile(null);
        setMobileFreshness([]);
      }
    })();
  }, [selectedUserId]);

  useEffect(() => {
    (async () => {
      try {
        const [healthResponse, infoResponse] = await Promise.all([getMobileHealth(), getServerInfo()]);
        setMobileHealth(healthResponse.data);
        const info = infoResponse.data || {};
        setServerInfo(info);
        if (info.local_ips?.length) {
          setServer((previous) => previous.ip === 'localhost' ? { ...previous, ip: info.local_ips[0] } : previous);
        }
      } catch {
        setMobileHealth({ status: 'offline', server: null, version: null, timestamp: null });
        setServerInfo({ hostname: null, localhost_url: null, local_ips: [], mobile_base_urls: [] });
      }
    })();
  }, []);

  const save = async () => {
    try {
      const response = await updateProfile(selectedUserId, contacts);
      setProfile(response.data?.profile || { ...profile, ...contacts });
      showToast('Settings saved');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const saveLocation = async () => {
    try {
      const payload = {
        location_label: locationForm.location_label.trim() || null,
        latitude: locationForm.latitude === '' ? null : Number(locationForm.latitude),
        longitude: locationForm.longitude === '' ? null : Number(locationForm.longitude),
      };
      if ((payload.latitude == null) !== (payload.longitude == null)) {
        showToast('Latitude and longitude must both be provided', 'error');
        return;
      }
      const response = await updateProfile(selectedUserId, payload);
      setProfile(response.data?.profile || { ...profile, ...payload });
      showToast(payload.latitude != null ? 'Location saved' : 'Location cleared');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const useCurrentLocation = async () => {
    if (!navigator.geolocation) {
      showToast('Browser geolocation is unavailable on this device', 'error');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocationForm((previous) => ({
          ...previous,
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6),
          location_label: previous.location_label || 'Current browser location',
        }));
        setLocating(false);
        showToast('Current location captured');
      },
      (error) => {
        setLocating(false);
        showToast(error.message || 'Location permission was denied', 'error');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    );
  };

  const connectSpotify = async () => {
    try {
      const response = await getSpotifySync(selectedUserId);
      if (response.data?.needs_auth && response.data?.auth_url) {
        window.location.href = response.data.auth_url;
        return;
      }
      showToast(
        response.data?.message || (response.data?.success ? 'Spotify synced' : 'Spotify is unavailable'),
        response.data?.success ? 'success' : 'warning'
      );
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const addUser = async () => {
    if (!newUser.id.trim() || !newUser.name.trim()) {
      showToast('User id and name are required', 'error');
      return;
    }
    try {
      const payload = {
        id: newUser.id.trim().toLowerCase(),
        name: newUser.name.trim(),
        age: newUser.age === '' ? null : Number(newUser.age),
        sex: newUser.sex,
        height_cm: newUser.height_cm === '' ? null : Number(newUser.height_cm)
      };
      await createUser(payload);
      const usersResponse = await getUsers();
      const nextUsers = Array.isArray(usersResponse.data) ? usersResponse.data : usersResponse.data?.users || [];
      setUsers(nextUsers);
      setSelectedUser(payload.id);
      setNewUser({ id: '', name: '', age: '', sex: 'female', height_cm: '' });
      showToast('User created successfully');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const openReflections = async () => {
    try {
      const response = await getReflections(selectedUserId);
      setReflections(response.data?.reflections || []);
      setShowReflectionModal(true);
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const groupedReflections = useMemo(() => reflections.reduce((acc, item) => {
    const key = item.agent_type || 'other';
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {}), [reflections]);

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-4">Users</div>
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <div className="text-sm font-semibold text-emerald-900">Active profile: {selectedUser.name}</div>
          <div className="text-xs text-emerald-700 mt-1">All dashboard metrics, doctor contacts, alerts, family state, and Spotify status shown below belong to `{selectedUser.id}` only.</div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="text-sm font-medium text-slate-700 mb-3">Existing Users</div>
            <div className="space-y-3">
              {users.map((user) => (
                <div key={user.id} className={`rounded-2xl border px-4 py-3 ${user.id === selectedUserId ? 'border-emerald-400 bg-emerald-50/90' : 'bg-slate-50/80 border-slate-200 backdrop-blur-sm'}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-800">{user.name}</div>
                      <div className="text-xs text-slate-500">{user.id} • {user.age ?? 'Age n/a'} • {user.sex || 'Sex n/a'}</div>
                    </div>
                    <button onClick={() => setSelectedUser(user.id)} className="text-sm font-medium text-emerald-700 hover:text-emerald-800">
                      {user.id === selectedUserId ? 'Selected' : 'Switch'}
                    </button>
                  </div>
                  <div className="text-sm text-slate-600 mt-2">
                    {demoUserNotes[user.id] || 'Custom user profile created from the Settings page for additional testing and demos.'}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-700 mb-3">Add User</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input value={newUser.id} onChange={(event) => setNewUser({ ...newUser, id: event.target.value })} placeholder="User id" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              <input value={newUser.name} onChange={(event) => setNewUser({ ...newUser, name: event.target.value })} placeholder="Full name" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              <input type="number" value={newUser.age} onChange={(event) => setNewUser({ ...newUser, age: event.target.value })} placeholder="Age" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              <input type="number" value={newUser.height_cm} onChange={(event) => setNewUser({ ...newUser, height_cm: event.target.value })} placeholder="Height (cm)" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              <select value={newUser.sex} onChange={(event) => setNewUser({ ...newUser, sex: event.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm md:col-span-2">
                <option value="female">female</option>
                <option value="male">male</option>
                <option value="other">other</option>
              </select>
            </div>
            <button onClick={addUser} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition mt-4">Create User</button>
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-4">Server Configuration</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input value={server.ip} onChange={(event) => setServer({ ...server, ip: event.target.value })} placeholder="IP" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          <input value={server.port} onChange={(event) => setServer({ ...server, port: event.target.value })} placeholder="Port" className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="text-xs text-slate-500 mt-3">
          For a real iPhone on your Wi-Fi, replace <span className="font-mono">localhost</span> with your Mac&apos;s LAN IP. Current mobile base URL: <span className="font-mono">{mobileBaseUrl}</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div className="glass-subcard px-4 py-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">Laptop Hostname</div>
            <div className="text-sm font-medium text-slate-900 mt-1">{serverInfo.hostname || 'Unknown'}</div>
            <div className="text-xs text-slate-500 mt-2">Local simulator URL</div>
            <div className="text-sm font-mono text-slate-800 mt-1">{serverInfo.localhost_url || 'http://127.0.0.1:8000'}</div>
          </div>
          <div className="glass-subcard px-4 py-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">Detected Laptop IPs</div>
            {serverInfo.mobile_base_urls?.length ? (
              <div className="space-y-2 mt-2">
                {serverInfo.mobile_base_urls.map((url) => (
                  <div key={url} className="glass-subcard px-3 py-2">
                    <div className="text-sm font-mono text-slate-800">{url}</div>
                    <div className="text-xs text-slate-500 mt-1">Use this on the iPhone when both devices are on the same Wi-Fi.</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-500 mt-2">No LAN IP detected yet. Connect the laptop to Wi-Fi and refresh this page.</div>
            )}
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-1">iPhone App Integration</div>
        <div className="text-sm text-slate-500 mb-4">Visible mobile sync status for {selectedUser.name}. The iOS app talks to the same backend as the web app.</div>
        <div className={`rounded-xl border px-4 py-3 mb-4 ${mobileHealth.status === 'ok' ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
          <div className="text-sm font-semibold text-slate-800">
            {mobileHealth.status === 'ok' ? 'Mobile API is reachable' : 'Mobile API is not responding'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Server: {mobileHealth.server || 'unknown'} • version {mobileHealth.version || 'unknown'} • last check {formatDateTime(mobileHealth.timestamp)}
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="glass-subcard px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">Active Mobile User</div>
              <div className="text-sm font-semibold text-slate-900 mt-1">{selectedUser.name} ({selectedUser.id})</div>
              <div className="text-xs text-slate-500 mt-1">Profile version: {mobileProfile?.profile_version || 'Not loaded yet'}</div>
              <div className="text-xs text-slate-500 mt-1">Last profile contract update: {formatDateTime(mobileProfile?.updated_at)}</div>
            </div>
            <div className="space-y-3">
              {mobileDataRows.map((item) => (
                <div key={item.source} className="glass-subcard px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-slate-900">{item.label}</div>
                    <div className={`text-xs font-medium uppercase tracking-wide ${item.status === 'fresh' ? 'text-emerald-700' : item.status === 'due_soon' ? 'text-amber-700' : 'text-red-700'}`}>
                      {String(item.status).replaceAll('_', ' ')}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 mt-2">Last sync: {formatDateTime(item.last_synced)}</div>
                  <div className="text-xs text-slate-500 mt-1">Recommended every {item.recommended_interval_days} days</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {item.days_since_upload == null ? 'No sync yet' : `${item.days_since_upload} days since last sync`}
                  </div>
                </div>
              ))}
              {!mobileDataRows.length && (
                <div className="empty-state-card px-4 py-3 text-sm text-slate-500">
                  No iPhone-originated sync has been recorded for this user yet.
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">
            <div className="glass-subcard px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">How It Works</div>
              <div className="text-sm text-slate-700 mt-2">1. Open the iOS app in Xcode from the existing `health_app` project.</div>
              <div className="text-sm text-slate-700 mt-1">2. Point the app to <span className="font-mono">{mobileBaseUrl}</span>.</div>
              <div className="text-sm text-slate-700 mt-1">3. Use the same EirView user id: <span className="font-mono">{selectedUser.id}</span>.</div>
              <div className="text-sm text-slate-700 mt-1">4. HealthKit and manual iPhone inputs sync into this user profile and update the same dashboard you see on the web.</div>
              <div className="text-sm text-slate-700 mt-1">5. On the web, successful phone syncs also show up in Data Ingest under iPhone / Apple sync activity and refresh windows.</div>
            </div>
            <div className="glass-subcard px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">Mobile Source Status</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                {Object.entries(mobileProfile?.source_status || {}).map(([key, value]) => (
                  <div key={key} className="glass-subcard px-3 py-2">
                    <div className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</div>
                    <div className="text-sm font-medium text-slate-800 mt-1">{value?.present ? 'Present' : 'Missing'}</div>
                    <div className="text-xs text-slate-500 mt-1">{formatDateTime(value?.last_sync)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-1">Medical Contacts</div>
        <div className="text-sm text-slate-500 mb-4">Editing doctor and emergency contacts for {selectedUser.name} ({selectedUser.id}).</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.keys(contacts).filter((key) => key !== 'privacy_level').map((key) => (
            <input key={key} value={contacts[key]} onChange={(event) => setContacts({ ...contacts, [key]: event.target.value })} placeholder={key.replace(/_/g, ' ')} className="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          ))}
        </div>
        <button onClick={save} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition mt-4">Save</button>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-1">Location & Weather</div>
        <div className="text-sm text-slate-500 mb-4">Weather, AQI, UV, and outdoor smart reminders use these saved coordinates when available. If empty, the app falls back to the default Bangalore demo location.</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            value={locationForm.location_label}
            onChange={(event) => setLocationForm({ ...locationForm, location_label: event.target.value })}
            placeholder="Location label"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="number"
            step="0.000001"
            value={locationForm.latitude}
            onChange={(event) => setLocationForm({ ...locationForm, latitude: event.target.value })}
            placeholder="Latitude"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="number"
            step="0.000001"
            value={locationForm.longitude}
            onChange={(event) => setLocationForm({ ...locationForm, longitude: event.target.value })}
            placeholder="Longitude"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={useCurrentLocation} disabled={locating} className="bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-60">
            {locating ? 'Capturing...' : 'Use Current Browser Location'}
          </button>
          <button onClick={saveLocation} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 text-sm font-medium transition">
            Save Location
          </button>
          <button
            onClick={() => setLocationForm({ location_label: '', latitude: '', longitude: '' })}
            className="border border-slate-300 rounded-lg px-4 py-2 text-sm text-slate-700 hover:border-slate-400 transition"
          >
            Clear Form
          </button>
        </div>
        <div className="mt-4 text-xs text-slate-500">
          Current saved location:
          {' '}
          <span className="font-mono text-slate-700">
            {profile?.latitude != null && profile?.longitude != null
              ? `${profile.location_label || 'Saved coordinates'} (${Number(profile.latitude).toFixed(4)}, ${Number(profile.longitude).toFixed(4)})`
              : 'Using Bangalore fallback'}
          </span>
        </div>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-1">Spotify Integration</div>
        <div className="text-sm text-slate-500 mb-4">Spotify is connected separately for each user profile. Recent tracks and sync snapshots below act as visible proof of what was actually pulled.</div>
        <div className={`mb-4 rounded-xl border px-4 py-3 ${spotifyStatus.connected ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}>
          <div className="text-sm font-semibold text-slate-800">
            {spotifyStatus.connected ? `Connected for ${selectedUser.name}` : `Not connected for ${selectedUser.name}`}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {spotifyStatus.connected
              ? `Last token update: ${spotifyStatus.connected_at || 'unknown'}`
              : 'Authorize Spotify while this user is active to keep listening insights tied to the correct profile.'}
          </div>
          {spotifyStatus.latest_sync && (
            <div className="text-xs text-slate-500 mt-2">
              Latest sync: {spotifyStatus.latest_sync.timestamp} • {spotifyStatus.latest_sync.track_count} tracks • valence {spotifyStatus.latest_sync.avg_valence}
            </div>
          )}
        </div>
        <button onClick={connectSpotify} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition">Connect Spotify</button>
        <div className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div>
            <div className="text-sm font-semibold text-slate-900">Recent Spotify Tracks</div>
            <div className="text-xs text-slate-500 mt-1">Most recent listening history saved for this profile.</div>
            {spotifyStatus.recent_tracks?.length ? (
              <div className="mt-4 space-y-3">
                {spotifyStatus.recent_tracks.map((track, index) => (
                  <div key={`${track.track_id || 'track'}-${track.played_at || index}`} className="glass-subcard flex items-center gap-3 px-3 py-3">
                    {track.album_image_url ? (
                      <img src={track.album_image_url} alt={track.album_name || track.track_name || 'Album art'} className="h-14 w-14 rounded-xl object-cover border border-slate-200/70" />
                    ) : (
                      <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-slate-100 text-xl">♪</div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-slate-900">{track.track_name || 'Unknown track'}</div>
                      <div className="truncate text-xs text-slate-500 mt-1">{track.artist_names || 'Unknown artist'}</div>
                      <div className="truncate text-xs text-slate-400 mt-1">{track.album_name || 'Unknown album'}</div>
                      <div className="text-[11px] text-slate-500 mt-2">Played {formatDateTime(track.played_at)}</div>
                    </div>
                    {track.spotify_url ? (
                      <a href={track.spotify_url} target="_blank" rel="noreferrer" className="text-xs font-medium text-emerald-700 hover:text-emerald-800">
                        Open
                      </a>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state-card mt-4 px-4 py-4 text-sm text-slate-500">
                No Spotify track history has been saved for this profile yet. After a successful sync, recent songs will appear here with album art and play timestamps.
              </div>
            )}
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Spotify Sync History</div>
            <div className="text-xs text-slate-500 mt-1">Snapshot timeline of mood metrics from each sync.</div>
            {spotifyStatus.sync_history?.length ? (
              <div className="mt-4 space-y-3">
                {spotifyStatus.sync_history.map((entry, index) => (
                  <div key={`${entry.timestamp || 'sync'}-${index}`} className="glass-subcard px-4 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-sm font-medium text-slate-900">{formatDateTime(entry.timestamp)}</div>
                      <div className={`text-xs font-semibold uppercase tracking-wide ${entry.flagged ? 'text-amber-700' : 'text-emerald-700'}`}>
                        {entry.flagged ? 'flagged' : 'normal'}
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
                      <div>
                        <div className="text-slate-500">Tracks</div>
                        <div className="mt-1 font-semibold text-slate-900">{entry.track_count ?? '—'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Valence</div>
                        <div className="mt-1 font-semibold text-slate-900">{entry.avg_valence ?? '—'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Energy</div>
                        <div className="mt-1 font-semibold text-slate-900">{entry.avg_energy ?? '—'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Danceability</div>
                        <div className="mt-1 font-semibold text-slate-900">{entry.avg_danceability ?? '—'}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state-card mt-4 px-4 py-4 text-sm text-slate-500">
                No Spotify sync snapshots yet. Once the account syncs, each pull will appear here with mood metrics.
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-4">Privacy Settings</div>
        <select value={contacts.privacy_level} onChange={(event) => setContacts({ ...contacts, privacy_level: event.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
          <option value="full">Full</option>
          <option value="summary">Summary</option>
          <option value="minimal">Minimal</option>
        </select>
      </div>
      <div className="glass-card p-6">
        <div className="font-semibold text-slate-900 mb-2">AI Learning</div>
        <div className="text-sm text-slate-500 mb-4">See what the AI has learned from past coach, mental health, and future-self conversations.</div>
        <button onClick={openReflections} className="bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-4 py-2 font-medium transition">
          What has the AI learned about me?
        </button>
      </div>
      <div className="rounded-2xl border border-red-200 bg-white/82 p-6 shadow-sm backdrop-blur-sm">
        <div className="font-semibold text-slate-900 mb-4">Danger Zone</div>
        <button onClick={() => setShowDeleteModal(true)} className="bg-red-500 hover:bg-red-600 text-white rounded-lg px-4 py-2 font-medium transition">Delete My Account</button>
      </div>
      {showReflectionModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="glass-card p-6 max-w-2xl w-full shadow-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-lg font-bold text-slate-900">What the AI has learned</h3>
              <button onClick={() => setShowReflectionModal(false)} className="text-sm text-slate-500 hover:text-slate-700 transition">Close</button>
            </div>
            {Object.keys(groupedReflections).length ? Object.entries(groupedReflections).map(([agentType, items]) => (
              <div key={agentType} className="mt-6">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{agentType.replaceAll('_', ' ')}</div>
                <div className="space-y-3 mt-3">
                  {items.map((item) => (
                    <div key={item.id} className="glass-subcard px-4 py-3">
                      <div className="text-sm text-slate-700 leading-relaxed">{item.reflection}</div>
                      <div className="text-xs text-slate-500 mt-2">{formatDateTime(item.created_at)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )) : <div className="text-sm text-slate-500 mt-6">No active reflections yet.</div>}
            <button
              onClick={async () => {
                try {
                  await clearReflections(selectedUserId);
                  setReflections([]);
                  showToast('Reflections cleared');
                } catch (error) {
                  showToast(error.message, 'error');
                }
              }}
              className="mt-6 rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:border-red-300 hover:text-red-600 transition"
            >
              Clear All Reflections
            </button>
          </div>
        </div>
      )}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="glass-card p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-red-600">Delete Account</h3>
            <p className="text-sm text-slate-600 mt-2">This will permanently delete all your health data, meal logs, reflections, achievements, and agent history. This cannot be undone.</p>
            <p className="text-sm text-slate-700 mt-3 font-medium">Type <code className="bg-red-50 text-red-600 px-1 rounded">DELETE</code> to confirm:</p>
            <input value={deleteConfirm} onChange={(event) => setDeleteConfirm(event.target.value)} className="border border-red-300 rounded-lg px-3 py-2 text-sm w-full mt-2" />
            <div className="flex gap-2 mt-4">
              <button onClick={() => { setShowDeleteModal(false); setDeleteConfirm(''); }} className="flex-1 border border-slate-300 rounded-lg px-4 py-2 text-sm">Cancel</button>
              <button
                disabled={deleteConfirm !== 'DELETE'}
                onClick={async () => {
                  try {
                    await deleteUser(selectedUserId);
                    const response = await getUsers();
                    const nextUsers = Array.isArray(response.data) ? response.data : response.data?.users || [];
                    setUsers(nextUsers);
                    if (nextUsers.length) setSelectedUser(nextUsers[0].id);
                    showToast('Account deleted');
                  } catch (error) {
                    showToast(error.message, 'error');
                  }
                  setShowDeleteModal(false);
                  setDeleteConfirm('');
                }}
                className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-40"
              >
                Delete Forever
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
