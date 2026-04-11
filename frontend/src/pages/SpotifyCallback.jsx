import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getProfile } from '../api';
import useStore from '../store';

const handledCodeKey = (code) => `eirview.spotify.callback.${code}`;

export default function SpotifyCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setProfile, setSelectedUser, showToast } = useStore();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state') || '';
    const error = searchParams.get('error');
    if (error) {
      showToast(`Spotify authorization failed: ${error}`, 'error');
      navigate('/settings', { replace: true });
      return;
    }
    if (!code) {
      showToast('Spotify callback is missing an authorization code', 'error');
      navigate('/settings', { replace: true });
      return;
    }
    if (sessionStorage.getItem(handledCodeKey(code)) === 'done') {
      navigate('/settings', { replace: true });
      return;
    }
    if (sessionStorage.getItem(handledCodeKey(code)) === 'processing') {
      return;
    }

    const run = async () => {
      sessionStorage.setItem(handledCodeKey(code), 'processing');
      try {
        const response = await fetch(`/api/spotify/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);
        const payload = await response.json();
        if (!response.ok || !payload?.success) {
          throw new Error(payload?.detail || payload?.message || 'Spotify sync failed');
        }
        sessionStorage.setItem(handledCodeKey(code), 'done');
        setSelectedUser(payload.user_id);
        const profileResponse = await getProfile(payload.user_id);
        setProfile(profileResponse.data);
        showToast('Spotify connected successfully');
      } catch (callbackError) {
        sessionStorage.removeItem(handledCodeKey(code));
        showToast(callbackError.message, 'error');
      } finally {
        navigate('/settings', { replace: true });
      }
    };

    run();
  }, [navigate, searchParams, setProfile, setSelectedUser, showToast]);

  return (
    <div className="glass-card p-8 text-center">
      <div className="text-lg font-semibold text-slate-900">Connecting Spotify</div>
      <div className="text-sm text-slate-500 mt-2">Finishing authorization and syncing recent listening data.</div>
    </div>
  );
}
