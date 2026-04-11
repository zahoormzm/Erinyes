import { CalendarDays, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getDashboard, getNutritionDay, resetTodayNutrition, uploadMeal } from '../api';
import ChatInterface from '../components/ChatInterface';
import FileUpload from '../components/FileUpload';
import MealAnalysis from '../components/MealAnalysis';
import NutritionTargets from '../components/NutritionTargets';
import NutritionTracker from '../components/NutritionTracker';
import useStore from '../store';

function formatDateTime(value) {
  if (!value) return null;
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? value.replace(' ', 'T') : value;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function formatDayLabel(value) {
  if (!value) return 'Unknown day';
  const parsed = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value.replace(' ', 'T'));
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
}

function groupMealsByDay(meals) {
  const grouped = new Map();
  meals.forEach((meal) => {
    const key = String(meal.timestamp || meal.date || '').slice(0, 10) || 'unknown';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(meal);
  });
  return Array.from(grouped.entries()).map(([day, dayMeals]) => ({ day, dayMeals }));
}

export default function Nutrition() {
  const { dashboard, selectedUserId, showToast, setDashboard } = useStore();
  const [analysis, setAnalysis] = useState(null);
  const [description, setDescription] = useState('');
  const [lightboxImage, setLightboxImage] = useState(null);
  const [selectedDay, setSelectedDay] = useState(() => new Date().toISOString().slice(0, 10));
  const [dayView, setDayView] = useState(null);
  const [resettingToday, setResettingToday] = useState(false);
  const todayKey = new Date().toISOString().slice(0, 10);
  const isTodayView = selectedDay === todayKey;
  const groupedMeals = groupMealsByDay(dayView?.meals || []);
  const nutritionData = dayView?.nutrition_targets || dashboard?.nutrition_targets;
  const waterForDay = dayView?.water_total_ml ?? dashboard?.water_today_ml ?? 0;
  const hasTodayEntries = isTodayView && ((dayView?.meals?.length || 0) > 0 || Number(waterForDay || 0) > 0);
  const selectedDayLabel = formatDayLabel(selectedDay);
  const emptyDayPreview = useMemo(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().slice(0, 10);
  }, []);
  const latestMealSummary = analysis
    ? {
        items: (analysis.items || []).map((item) => ({
          item: item.item,
          portion_g: item.portion_g,
          calories: item.calories,
          protein_g: item.protein_g,
          sat_fat_g: item.sat_fat_g
        })),
        total: analysis.total,
        flags: analysis.flags,
        score: analysis.health_score || analysis.score
      }
    : null;
  const nutritionContext = [
    `User: ${selectedUserId}`,
    `Viewing day: ${selectedDay}`,
    `Nutrition targets: ${nutritionData ? JSON.stringify(nutritionData) : 'unavailable'}`,
    `Meals for selected day: ${(dayView?.meals || []).slice(0, 3).map((meal) => `${meal.description || 'Meal entry'} (${meal.calories || meal.nutrition?.calories || 0} cal)`).join('; ') || 'none logged'}`,
    `Latest meal analysis: ${latestMealSummary ? JSON.stringify(latestMealSummary) : 'none yet on this page'}`
  ].join('\n');

  const refreshDashboard = async () => {
    const response = await getDashboard(selectedUserId);
    setDashboard(response.data);
  };

  const loadDayView = async (day) => {
    const response = await getNutritionDay(selectedUserId, day);
    setDayView(response.data);
  };

  useEffect(() => {
    if (!selectedUserId) return;
    loadDayView(selectedDay).catch((error) => showToast(error.message, 'error'));
  }, [selectedUserId, selectedDay]);

  const handleMealResult = async (payload) => {
    setAnalysis(payload);
    await refreshDashboard();
    await loadDayView(selectedDay);
  };

  const uploadPhoto = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', selectedUserId);
    return uploadMeal(formData);
  };

  const analyzeText = async () => {
    try {
      const response = await uploadMeal({ user_id: selectedUserId, description });
      await handleMealResult(response.data);
      setDescription('');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  const shiftDay = (delta) => {
    const next = new Date(`${selectedDay}T12:00:00`);
    next.setDate(next.getDate() + delta);
    setSelectedDay(next.toISOString().slice(0, 10));
  };

  const handleResetToday = async () => {
    if (!hasTodayEntries || resettingToday) return;
    setResettingToday(true);
    try {
      const response = await resetTodayNutrition(selectedUserId);
      setAnalysis(null);
      setDescription('');
      setDayView(response.data);
      await refreshDashboard();
      showToast(`Removed ${response.data.meals_deleted || 0} meal entries and ${response.data.water_entries_deleted || 0} water entries from today.`);
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setResettingToday(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              <CalendarDays size={14} />
              Daily Nutrition View
            </div>
            <div className="mt-3 text-lg font-semibold text-slate-900">{selectedDayLabel}</div>
            <div className="mt-1 text-sm text-slate-500">
              Switch days to show a clean nutrition slate. Days without meal or water logs automatically reset to zero.
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => shiftDay(-1)} className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-50">
                <ChevronLeft size={16} />
              </button>
              <input
                type="date"
                value={selectedDay}
                onChange={(event) => setSelectedDay(event.target.value)}
                className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
              />
              <button type="button" onClick={() => shiftDay(1)} className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-50">
                <ChevronRight size={16} />
              </button>
            </div>
            <button
              type="button"
              onClick={() => setSelectedDay(todayKey)}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => setSelectedDay(emptyDayPreview)}
              className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-100"
            >
              Preview Clean Day
            </button>
            <button
              type="button"
              onClick={() => setSelectedDay(emptyDayPreview)}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <span className="inline-flex items-center gap-2"><RotateCcw size={15} /> Reset View</span>
            </button>
            <button
              type="button"
              onClick={handleResetToday}
              disabled={!hasTodayEntries || resettingToday}
              className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            >
              {resettingToday ? 'Resetting...' : 'Reset Today Nutrition'}
            </button>
          </div>
        </div>
      </div>
      <NutritionTargets
        data={nutritionData}
        title={`Nutrition Targets For ${selectedDayLabel}`}
        subtitle={isTodayView ? 'This is your live daily intake view.' : `Viewing ${selectedDayLabel}. If there are no logs on this day, the nutrition totals reset to zero.`}
      />
      <NutritionTracker currentOverride={waterForDay} readOnly={!isTodayView} dayLabel={selectedDayLabel} />
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6 space-y-4 hover:shadow-md transition-shadow">
        <FileUpload
          accept=".jpg,.jpeg,.png"
          label="Meal Photo"
          endpoint={uploadPhoto}
          onUpload={handleMealResult}
          disabled={!isTodayView}
          disabledMessage="Switch back to Today to upload a meal photo. This screen is in preview mode for another date."
        />
        <div className="text-center text-slate-400 text-sm">-- or --</div>
        <div className="flex gap-2">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={`Describe what you ate with quantities, e.g.:\n2 rotis with dal (1 bowl)\n1 cup rice\n150g chicken breast\n1 glass buttermilk`}
            rows={3}
            className="border border-slate-300 rounded-xl px-3 py-2 text-sm flex-1 resize-none"
            disabled={!isTodayView}
          />
          <button disabled={!isTodayView} onClick={analyzeText} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition disabled:cursor-not-allowed disabled:opacity-50">Analyze</button>
        </div>
        {!isTodayView ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">Meal logging is disabled while you are viewing another date. Switch back to Today to add new food entries.</div> : null}
      </div>
      <MealAnalysis analysis={analysis} />
      <ChatInterface
        chatType="coach"
        userId={selectedUserId}
        title={analysis ? 'Ask AI About This Meal' : 'Nutrition Coach'}
        placeholder={analysis ? 'Ask what is good, bad, or what to change in this meal' : 'Ask about your meals, targets, or what to eat next'}
        helperText={
          analysis
            ? 'The uploaded meal above is included automatically in this chat context, along with your nutrition targets and recent meals.'
            : `The coach uses your nutrition targets and the meals visible for ${selectedDayLabel}.`
        }
        suggestedPrompts={
          analysis
            ? [
                'What is wrong with this meal for my current targets?',
                'What should I change in this exact meal?',
                'If I eat this, what should my next meal look like?'
              ]
            : [
                'What should I eat next based on this analysis?',
                'Where is this meal off relative to my targets?',
                'How can I improve my protein and keep calories controlled?'
              ]
        }
        context={nutritionContext}
      />
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 shadow-sm p-6 hover:shadow-md transition-shadow">
        <div className="font-semibold text-slate-900 mb-4">Meals For {selectedDayLabel}</div>
        {groupedMeals.length ? groupedMeals.map(({ day, dayMeals }) => (
          <div key={day} className="mb-5 last:mb-0">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{formatDayLabel(day)}</div>
            <div className="space-y-3">
              {dayMeals.map((meal) => (
                <div key={meal.id} className="rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3">
                  <div className="flex items-start gap-4">
                    {meal.image_url ? (
                      <img
                        src={meal.image_url}
                        alt={meal.description}
                        className="w-16 h-16 rounded-lg object-cover border border-slate-200 cursor-pointer hover:ring-2 hover:ring-emerald-400 transition"
                        onClick={() => setLightboxImage(meal.image_url)}
                      />
                    ) : null}
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-700">{meal.description || 'Meal entry'}</div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                        <span>Logged on {formatDateTime(meal.timestamp || meal.date) || meal.date}</span>
                        <span>{meal.calories || meal.nutrition?.calories || 0} cal</span>
                        {meal.photo_path ? <span>Photo analysis</span> : <span>Meal entry</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )) : <div className="text-sm text-slate-500">No meals are logged for this day yet. This view is intentionally zeroed so you can demo a fresh day.</div>}
      </div>
      {lightboxImage ? (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setLightboxImage(null)}>
          <img src={lightboxImage} alt="Meal" className="max-w-full max-h-[80vh] rounded-xl shadow-2xl" />
        </div>
      ) : null}
    </div>
  );
}
