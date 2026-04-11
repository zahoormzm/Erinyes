import { AlertTriangle } from 'lucide-react';
import { notifyDoctor } from '../api';
import useStore from '../store';

export default function AlertBanner() {
  const { alerts, selectedUserId, setAlerts, showToast } = useStore();
  if (!alerts?.length) return null;

  const dismiss = (id) => setAlerts(alerts.filter((alert) => alert.id !== id));
  const send = async (id) => {
    try {
      const response = await notifyDoctor(selectedUserId, id);
      showToast(response.data?.success ? 'Doctor notified with full evidence report' : 'Doctor notification failed', response.data?.success ? 'success' : 'error');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  return (
    <div className="px-6 pt-4">
      {alerts.map((alert) => (
        <div key={alert.id} className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-red-500" size={18} />
            <div className="text-red-800 text-sm font-medium flex-1">{alert.flag_reason || alert.message || `ALERT: ${alert.metric} reading of ${alert.value} is critically ${alert.direction || 'abnormal'}.`}</div>
            <button onClick={() => dismiss(alert.id)} className="border border-slate-300 text-slate-700 rounded-lg px-4 py-2 hover:bg-slate-50">Dismiss</button>
            {alert.doctor_available && <button onClick={() => send(alert.id)} className="bg-red-500 hover:bg-red-600 text-white rounded-lg px-4 py-2 font-medium transition">Notify Doctor</button>}
          </div>
          {alert.doctor_report_summary?.headline && <div className="text-red-700 text-xs mt-2">{alert.doctor_report_summary.headline}</div>}
          {alert.metric === 'phq9_score' && alert.value > 20 && (
            <div className="text-red-700 text-xs mt-2">Crisis helplines: Vandrevala Foundation 1860-2662-345 | iCall 9152987821 | AASRA 9820466726</div>
          )}
        </div>
      ))}
    </div>
  );
}
