import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import AlertBanner from './components/AlertBanner';
import Dashboard from './pages/Dashboard';
import DataIngest from './pages/DataIngest';
import Insights from './pages/Insights';
import ResearchLab from './pages/ResearchLab';
import Mental from './pages/Mental';
import Nutrition from './pages/Nutrition';
import FutureSelf from './pages/FutureSelf';
import Activity from './pages/Activity';
import Posture from './pages/Posture';
import Gamification from './pages/Gamification';
import Family from './pages/Family';
import Settings from './pages/Settings';
import SpotifyCallback from './pages/SpotifyCallback';
import useStore from './store';
import { getAlerts, getDashboard, getGamification, getProfile, getUsers } from './api';

export default function App() {
  const {
    selectedUserId,
    setUsers,
    setDashboard,
    setGamification,
    setAlerts,
    setProfile,
    toast,
    showToast,
    setSelectedUser,
  } = useStore();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const response = await getUsers();
        const nextUsers = Array.isArray(response.data) ? response.data : response.data.users || [];
        setUsers(nextUsers);
        if (nextUsers.length && !nextUsers.some((user) => user.id === selectedUserId)) {
          setSelectedUser(nextUsers[0].id);
        }
      } catch (error) {
        showToast(error.message, 'error');
      }
    })();
  }, [selectedUserId, setSelectedUser, setUsers, showToast]);

  useEffect(() => {
    if (!selectedUserId) return;
    (async () => {
      try {
        const [dashboardResponse, gamificationResponse, alertsResponse, profileResponse] = await Promise.all([
          getDashboard(selectedUserId),
          getGamification(selectedUserId),
          getAlerts(selectedUserId),
          getProfile(selectedUserId)
        ]);
        setDashboard(dashboardResponse.data);
        setGamification(gamificationResponse.data);
        setAlerts(alertsResponse.data);
        setProfile(profileResponse.data);
      } catch (error) {
        if (error?.response?.status === 404) {
          setDashboard(null);
          setProfile(null);
          return;
        }
        showToast(error.message, 'error');
      }
    })();
  }, [selectedUserId, setAlerts, setDashboard, setGamification, setProfile, showToast]);

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 overflow-x-hidden">
        <Sidebar mobileOpen={mobileSidebarOpen} onClose={() => setMobileSidebarOpen(false)} />
        <div className="flex-1 md:ml-64 min-w-0">
          <TopBar onMenu={() => setMobileSidebarOpen(true)} />
          <AlertBanner />
          <main key={selectedUserId} className="max-w-7xl mx-auto px-4 md:px-6 py-6 min-w-0 animate-fade-in">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/ingest" element={<DataIngest />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/research" element={<ResearchLab />} />
              <Route path="/mental" element={<Mental />} />
              <Route path="/nutrition" element={<Nutrition />} />
              <Route path="/future" element={<FutureSelf />} />
              <Route path="/activity" element={<Activity />} />
              <Route path="/posture" element={<Posture />} />
              <Route path="/gamification" element={<Gamification />} />
              <Route path="/family" element={<Family />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/callback" element={<SpotifyCallback />} />
              <Route path="*" element={<Dashboard />} />
            </Routes>
          </main>
        </div>
        {toast && (
          <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-white text-sm font-medium transition-all ${
            toast.type === 'success' ? 'bg-emerald-500' :
            toast.type === 'error' ? 'bg-red-500' :
            toast.type === 'warning' ? 'bg-amber-500' : 'bg-blue-500'
          }`}>
            {toast.message}
          </div>
        )}
      </div>
    </BrowserRouter>
  );
}
