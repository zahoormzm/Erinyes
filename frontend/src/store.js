import { create } from 'zustand';

let toastTimer = null;

const useStore = create((set, get) => ({
  selectedUserId: 'zahoor',
  users: [],
  profile: null,
  dashboard: null,
  insightSimulation: null,
  gamification: null,
  reminders: [],
  alerts: [],
  loading: false,
  toast: null,
  chatMessages: {},
  getChatMessages: (chatType) => get().chatMessages[chatType] || [],
  setChatMessages: (chatType, messages) => set((state) => ({
    chatMessages: { ...state.chatMessages, [chatType]: typeof messages === 'function' ? messages(state.chatMessages[chatType] || []) : messages }
  })),
  clearChat: (chatType) => set((state) => ({
    chatMessages: { ...state.chatMessages, [chatType]: [] }
  })),
  setSelectedUser: (id) => set((state) => state.selectedUserId === id ? state : {
    selectedUserId: id,
    profile: null,
    dashboard: null,
    insightSimulation: null,
    gamification: null,
    reminders: [],
    alerts: [],
    chatMessages: {}
  }),
  setUsers: (users) => set({ users }),
  setProfile: (profile) => set({ profile }),
  setDashboard: (dashboard) => set({ dashboard }),
  setInsightSimulation: (insightSimulation) => set({ insightSimulation }),
  setGamification: (gamification) => set({ gamification }),
  setReminders: (reminders) => set({ reminders }),
  setAlerts: (alerts) => set({ alerts }),
  setLoading: (loading) => set({ loading }),
  showToast: (message, type = 'success') => {
    if (toastTimer) window.clearTimeout(toastTimer);
    set({ toast: { message, type } });
    toastTimer = window.setTimeout(() => set({ toast: null }), 5000);
  }
}));

export default useStore;
