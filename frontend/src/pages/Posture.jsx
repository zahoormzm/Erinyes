import { Camera, CirclePause, Play, ScanLine, Volume2, VolumeX } from 'lucide-react';
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';
import { useEffect, useMemo, useRef, useState } from 'react';
import Webcam from 'react-webcam';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getPostureHistory, savePostureReading } from '../api';
import useStore from '../store';

const MEDIAPIPE_WASM_BASE = '/mediapipe';
const MEDIAPIPE_POSE_MODEL = '/models/pose_landmarker_lite.task';
const POSE_INDEX = {
  LEFT_EAR: 7,
  RIGHT_EAR: 8,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_HIP: 23,
  RIGHT_HIP: 24
};

let poseLandmarkerPromise = null;

async function getPoseLandmarker() {
  if (!poseLandmarkerPromise) {
    poseLandmarkerPromise = (async () => {
      const filesetResolver = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_BASE);
      return PoseLandmarker.createFromOptions(filesetResolver, {
        baseOptions: { modelAssetPath: MEDIAPIPE_POSE_MODEL },
        runningMode: 'VIDEO',
        numPoses: 1
      });
    })().catch((error) => {
      poseLandmarkerPromise = null;
      throw error;
    });
  }
  return poseLandmarkerPromise;
}

function calculateAngle(ear, shoulder, hip) {
  const vec1 = [ear.x - shoulder.x, ear.y - shoulder.y];
  const vec2 = [hip.x - shoulder.x, hip.y - shoulder.y];
  const norm1 = Math.hypot(vec1[0], vec1[1]);
  const norm2 = Math.hypot(vec2[0], vec2[1]);
  if (!norm1 || !norm2) return 180;
  const cosine = Math.max(-1, Math.min(1, ((vec1[0] * vec2[0]) + (vec1[1] * vec2[1])) / (norm1 * norm2)));
  return (Math.acos(cosine) * 180) / Math.PI;
}

function angleToScore(angle) {
  if (angle >= 170) return 100;
  if (angle >= 160) return 80;
  if (angle >= 150) return 60;
  if (angle >= 140) return 40;
  return 20;
}

function pickVisibleTriplet(landmarks) {
  const left = {
    ear: landmarks[POSE_INDEX.LEFT_EAR],
    shoulder: landmarks[POSE_INDEX.LEFT_SHOULDER],
    hip: landmarks[POSE_INDEX.LEFT_HIP]
  };
  const right = {
    ear: landmarks[POSE_INDEX.RIGHT_EAR],
    shoulder: landmarks[POSE_INDEX.RIGHT_SHOULDER],
    hip: landmarks[POSE_INDEX.RIGHT_HIP]
  };
  const leftVisibility = (left.ear?.visibility ?? 0) + (left.shoulder?.visibility ?? 0) + (left.hip?.visibility ?? 0);
  const rightVisibility = (right.ear?.visibility ?? 0) + (right.shoulder?.visibility ?? 0) + (right.hip?.visibility ?? 0);
  return leftVisibility >= rightVisibility ? left : right;
}

async function screenshotToImage(dataUrl) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  return image;
}

function postureLabel(score) {
  if (score == null) return 'No reading yet';
  if (score >= 85) return 'Strong alignment';
  if (score >= 65) return 'Mostly aligned';
  if (score >= 50) return 'Needs correction';
  return 'Slouching detected';
}

function drawPoint(ctx, point, color) {
  ctx.beginPath();
  ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();
}

function drawSegment(ctx, from, to, color) {
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.lineCap = 'round';
  ctx.stroke();
}

function clearCanvas(canvas) {
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawOverlay(canvas, video, analysis) {
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx || !video) return;
  const width = video.videoWidth || 0;
  const height = video.videoHeight || 0;
  if (!width || !height) return;
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;
  ctx.clearRect(0, 0, width, height);
  if (!analysis?.landmarks) return;

  const toCanvas = (landmark) => ({
    x: width - (landmark.x * width),
    y: landmark.y * height
  });

  const ear = toCanvas(analysis.landmarks.ear);
  const shoulder = toCanvas(analysis.landmarks.shoulder);
  const hip = toCanvas(analysis.landmarks.hip);
  const scoreColor = analysis.score >= 65 ? '#10b981' : analysis.score >= 50 ? '#f59e0b' : '#ef4444';

  drawSegment(ctx, ear, shoulder, scoreColor);
  drawSegment(ctx, shoulder, hip, scoreColor);
  drawPoint(ctx, ear, '#38bdf8');
  drawPoint(ctx, shoulder, '#f97316');
  drawPoint(ctx, hip, '#a855f7');

  ctx.fillStyle = 'rgba(15, 23, 42, 0.72)';
  ctx.fillRect(12, 12, 170, 56);
  ctx.fillStyle = '#ffffff';
  ctx.font = '600 14px sans-serif';
  ctx.fillText(`Score ${analysis.score}%`, 24, 34);
  ctx.font = '500 12px sans-serif';
  ctx.fillText(`Angle ${analysis.angle.toFixed(1)}°`, 24, 54);
}

export default function Posture() {
  const webcamRef = useRef(null);
  const overlayRef = useRef(null);
  const intervalRef = useRef(null);
  const animationRef = useRef(null);
  const latestAnalysisRef = useRef(null);
  const audioContextRef = useRef(null);
  const lastAlertAtRef = useRef(0);
  const { selectedUserId, profile, showToast } = useStore();
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [backendIssue, setBackendIssue] = useState('');
  const [soundAlertsEnabled, setSoundAlertsEnabled] = useState(true);
  const chartData = useMemo(
    () => history.map((row, index) => ({ sample: index + 1, score: Number(row.score_pct || 0), angle: Number(row.avg_angle || 0) })),
    [history]
  );

  const load = async () => {
    try {
      const response = await getPostureHistory(selectedUserId);
      setSummary(response.data.summary);
      setHistory(response.data.history || []);
      setBackendIssue('');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const stopAutoCheck = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setRunning(false);
  };

  const playAlertTone = () => {
    if (!soundAlertsEnabled) return;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContextClass();
    }
    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.type = 'triangle';
    oscillator.frequency.value = 660;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.08, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.26);
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.28);
  };

  const analyzeCurrentFrame = async () => {
    const video = webcamRef.current?.video;
    if (!video || video.readyState < 2) return null;
    const landmarker = await getPoseLandmarker();
    const result = landmarker.detectForVideo(video, performance.now());
    const landmarks = result?.landmarks?.[0];
    if (!landmarks?.length) return null;
    const { ear, shoulder, hip } = pickVisibleTriplet(landmarks);
    if (!ear || !shoulder || !hip) return null;
    const angle = Number(calculateAngle(ear, shoulder, hip).toFixed(1));
    const score = angleToScore(angle);
    return { landmarks: { ear, shoulder, hip }, angle, score };
  };

  const capture = async () => {
    if (!webcamRef.current || loading) return;
    setLoading(true);
    try {
      const analysis = latestAnalysisRef.current || await analyzeCurrentFrame();
      if (!analysis) {
        throw new Error('No body pose detected. Make sure one ear, shoulder, and hip are visible in the frame.');
      }
      latestAnalysisRef.current = analysis;
      await savePostureReading(selectedUserId, {
        score_pct: analysis.score,
        avg_angle: analysis.angle,
        is_slouching: analysis.score < 60
      });
      await load();
      setBackendIssue('');
      showToast(`Posture checked: ${analysis.score}%`);
    } catch (error) {
      setBackendIssue(String(error.message || 'Posture analysis is unavailable on this browser right now.'));
      showToast(error.message, 'error');
      stopAutoCheck();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    stopAutoCheck();
    latestAnalysisRef.current = null;
    clearCanvas(overlayRef.current);
    load();
  }, [selectedUserId]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      if (animationRef.current) window.cancelAnimationFrame(animationRef.current);
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      try {
        const analysis = await analyzeCurrentFrame();
        latestAnalysisRef.current = analysis;
        if (analysis) {
          drawOverlay(overlayRef.current, webcamRef.current?.video, analysis);
          setBackendIssue('');
          if (running && soundAlertsEnabled && analysis.score < 55 && Date.now() - lastAlertAtRef.current > 12000) {
            lastAlertAtRef.current = Date.now();
            playAlertTone();
          }
        } else {
          clearCanvas(overlayRef.current);
        }
      } catch (error) {
        latestAnalysisRef.current = null;
        clearCanvas(overlayRef.current);
        setBackendIssue(String(error.message || 'Live posture overlay is unavailable on this browser right now.'));
      } finally {
        if (!cancelled) {
          animationRef.current = window.requestAnimationFrame(tick);
        }
      }
    };

    animationRef.current = window.requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      if (animationRef.current) window.cancelAnimationFrame(animationRef.current);
    };
  }, []);

  const startAutoCheck = () => {
    if (running) return;
    setRunning(true);
    capture();
    intervalRef.current = window.setInterval(capture, 5000);
  };

  const currentScore = summary?.latest_score_pct ?? profile?.posture_score_pct ?? null;

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="flex items-center gap-2 text-slate-900 font-semibold">
              <ScanLine size={18} className="text-emerald-600" />
              Live Posture Check
            </div>
            <div className="text-sm text-slate-500 mt-2 max-w-2xl">
              Use your laptop camera to estimate posture from your head, shoulders, and torso in the browser. The reading is saved to the active user profile only.
            </div>
          </div>
          <div className={`rounded-2xl px-4 py-3 border ${currentScore != null && currentScore >= 65 ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
            <div className="text-xs uppercase tracking-wide text-slate-500">Current Posture</div>
            <div className="text-2xl font-semibold text-slate-900 mt-1">{currentScore != null ? `${currentScore}%` : '—'}</div>
            <div className="text-sm text-slate-600 mt-1">{postureLabel(currentScore)}</div>
          </div>
        </div>
        {backendIssue && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {backendIssue}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
        <div className="glass-card p-6">
          <div className="aspect-video overflow-hidden rounded-2xl bg-slate-950 relative">
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              mirrored
              videoConstraints={{ facingMode: 'user' }}
              className="h-full w-full object-cover"
            />
            <canvas
              ref={overlayRef}
              className="absolute inset-0 h-full w-full pointer-events-none"
            />
          </div>
          <div className="flex flex-wrap gap-3 mt-4">
            <button onClick={capture} disabled={loading} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition disabled:opacity-60">
              <span className="inline-flex items-center gap-2"><Camera size={16} /> Capture Reading</span>
            </button>
            {!running ? (
              <button onClick={startAutoCheck} disabled={loading} className="bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-4 py-2 font-medium transition disabled:opacity-60">
                <span className="inline-flex items-center gap-2"><Play size={16} /> Start Auto Check</span>
              </button>
            ) : (
              <button onClick={stopAutoCheck} className="bg-amber-500 hover:bg-amber-600 text-white rounded-lg px-4 py-2 font-medium transition">
                <span className="inline-flex items-center gap-2"><CirclePause size={16} /> Stop Auto Check</span>
              </button>
            )}
            <button
              onClick={() => setSoundAlertsEnabled((current) => !current)}
              className={`rounded-lg px-4 py-2 font-medium transition border ${soundAlertsEnabled ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100' : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
            >
              <span className="inline-flex items-center gap-2">
                {soundAlertsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                {soundAlertsEnabled ? 'Sound alerts on' : 'Sound alerts off'}
              </span>
            </button>
          </div>
          <div className="text-xs text-slate-500 mt-4">
            Best results: sit slightly side-on so one ear, shoulder, and hip are visible, keep your upper body in frame, and allow browser camera access when prompted. The overlay now shows the exact landmarks and line being scored. During auto-check, a soft tone plays roughly every 12 seconds if posture stays poor.
          </div>
        </div>

        <div className="space-y-6">
          <div className="glass-card p-6">
            <div className="text-sm font-semibold text-slate-900">Latest Reading</div>
            <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
              <div className="glass-subcard px-4 py-3">
                <div className="text-slate-500">Score</div>
                <div className="text-xl font-semibold text-slate-900 mt-1">{summary?.latest_score_pct != null ? `${summary.latest_score_pct}%` : '—'}</div>
              </div>
              <div className="glass-subcard px-4 py-3">
                <div className="text-slate-500">Angle</div>
                <div className="text-xl font-semibold text-slate-900 mt-1">{summary?.latest_angle != null ? `${summary.latest_angle}°` : '—'}</div>
              </div>
              <div className="glass-subcard px-4 py-3">
                <div className="text-slate-500">Average</div>
                <div className="text-xl font-semibold text-slate-900 mt-1">{summary?.average_score_pct != null ? `${summary.average_score_pct}%` : '—'}</div>
              </div>
              <div className="glass-subcard px-4 py-3">
                <div className="text-slate-500">Status</div>
                <div className={`text-xl font-semibold mt-1 ${summary?.is_slouching ? 'text-red-600' : 'text-emerald-600'}`}>
                  {summary?.is_slouching == null ? '—' : summary.is_slouching ? 'Slouching' : 'Aligned'}
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <div className="text-sm font-semibold text-slate-900 mb-4">Trend</div>
            {chartData.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="sample" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#10b981" strokeWidth={3} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-sm text-slate-500">No posture history yet. Capture your first reading.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
