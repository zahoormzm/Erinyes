import { ChevronRight } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getProfile, updateProfile } from '../api';
import useStore from '../store';

function Section({ title, open, toggle, children }) {
  return (
    <div>
      <div className="flex items-center justify-between cursor-pointer py-3 border-b border-slate-200/70" onClick={toggle}>
        <span className="font-medium text-slate-700">{title}</span>
        <ChevronRight size={18} className={`transform transition-transform ${open ? 'rotate-90' : ''}`} />
      </div>
      {open && <div className="py-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{children}</div>}
    </div>
  );
}

const inputClass = 'border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 w-full';

export default function ManualEntryForm({ refreshKey = 0 }) {
  const { selectedUserId, showToast, setProfile } = useStore();
  const [form, setForm] = useState({});
  const [open, setOpen] = useState({ blood: true, body: false, vitals: false, lifestyle: false, academic: true, family: false, contacts: false });

  useEffect(() => {
    (async () => {
      try {
        const response = await getProfile(selectedUserId);
        setForm(response.data);
      } catch (error) {
        showToast(error.message, 'error');
      }
    })();
  }, [selectedUserId, showToast, refreshKey]);

  const setValue = (key, value) => setForm((previous) => ({ ...previous, [key]: value }));
  const fields = useMemo(() => ({
    blood: [['ldl', 'LDL'], ['hdl', 'HDL'], ['triglycerides', 'Triglycerides'], ['total_cholesterol', 'Total Cholesterol'], ['fasting_glucose', 'Fasting Glucose'], ['hba1c', 'HbA1c'], ['vitamin_d', 'Vitamin D'], ['ferritin', 'Iron/Ferritin'], ['b12', 'Vitamin B12'], ['tsh', 'TSH'], ['hemoglobin', 'Hemoglobin']],
    body: [['weight_kg', 'Weight kg'], ['height_cm', 'Height cm'], ['bmi', 'BMI'], ['body_fat_pct', 'Body Fat %'], ['muscle_mass_kg', 'Muscle Mass'], ['bone_mass_kg', 'Bone Mass']],
    vitals: [['resting_hr', 'Resting HR'], ['hrv_ms', 'HRV ms'], ['vo2max', 'VO2max'], ['blood_oxygen_pct', 'SpO2 %'], ['blood_pressure_systolic', 'Blood Pressure Systolic'], ['blood_pressure_diastolic', 'Blood Pressure Diastolic'], ['respiratory_rate', 'Respiratory Rate']],
    lifestyle: [['exercise_hours_week', 'Exercise hours/week'], ['sleep_hours', 'Sleep hours average'], ['sleep_target', 'Sleep target'], ['screen_time_hours', 'Screen time hours/day'], ['stress_level', 'Stress level']],
    contacts: [['doctor_name', 'Doctor name'], ['doctor_email', 'Doctor email'], ['doctor_phone', 'Doctor phone'], ['emergency_contact_name', 'Emergency contact name'], ['emergency_contact_phone', 'Emergency phone']]
  }), []);

  const save = async () => {
    try {
      const response = await updateProfile(selectedUserId, form);
      setProfile(response.data.profile || form);
      showToast('Profile updated successfully');
    } catch (error) {
      showToast('Failed to update profile', 'error');
    }
  };

  const renderInputs = (items) => items.map(([key, label]) => (
    <div key={key}>
      <label className="text-xs text-slate-500">{label}</label>
      <input type="number" value={form[key] ?? ''} onChange={(event) => setValue(key, event.target.value === '' ? null : Number(event.target.value))} className={inputClass} />
    </div>
  ));

  return (
    <div className="glass-card p-6">
      <Section title="Blood Work" open={open.blood} toggle={() => setOpen((previous) => ({ ...previous, blood: !previous.blood }))}>{renderInputs(fields.blood)}</Section>
      <Section title="Body Composition" open={open.body} toggle={() => setOpen((previous) => ({ ...previous, body: !previous.body }))}>{renderInputs(fields.body)}</Section>
      <Section title="Vitals (HealthKit)" open={open.vitals} toggle={() => setOpen((previous) => ({ ...previous, vitals: !previous.vitals }))}>{renderInputs(fields.vitals)}</Section>
      <Section title="Lifestyle" open={open.lifestyle} toggle={() => setOpen((previous) => ({ ...previous, lifestyle: !previous.lifestyle }))}>
        {renderInputs(fields.lifestyle)}
        <div>
          <label className="text-xs text-slate-500">Smoking</label>
          <select value={form.smoking || 'never'} onChange={(event) => setValue('smoking', event.target.value)} className={inputClass}>
            <option>never</option>
            <option>former</option>
            <option>current</option>
          </select>
        </div>
      </Section>
      <Section title="Academic" open={open.academic} toggle={() => setOpen((previous) => ({ ...previous, academic: !previous.academic }))}>
        <div>
          <label className="text-xs text-slate-500">Current GPA/CGPA</label>
          <input type="number" step="0.01" value={form.academic_gpa ?? ''} onChange={(event) => setValue('academic_gpa', event.target.value === '' ? null : Number(event.target.value))} className={inputClass} />
        </div>
        <div>
          <label className="text-xs text-slate-500">Study hours per day</label>
          <input type="number" step="0.5" value={form.study_hours_daily ?? ''} onChange={(event) => setValue('study_hours_daily', event.target.value === '' ? null : Number(event.target.value))} className={inputClass} />
        </div>
        <div>
          <label className="text-xs text-slate-500">Exam/Academic stress</label>
          <input type="range" min="1" max="10" value={form.exam_stress ?? 5} onChange={(event) => setValue('exam_stress', Number(event.target.value))} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-500 mt-3" />
        </div>
        <div>
          <label className="text-xs text-slate-500">Academic year</label>
          <select value={form.academic_year || 'Year 1'} onChange={(event) => setValue('academic_year', event.target.value)} className={inputClass}>
            <option>Year 1</option>
            <option>Year 2</option>
            <option>Year 3</option>
            <option>Year 4</option>
            <option>Postgrad</option>
            <option>Not a student</option>
          </select>
        </div>
      </Section>
      <Section title="Family History" open={open.family} toggle={() => setOpen((previous) => ({ ...previous, family: !previous.family }))}>
        {['family_diabetes', 'family_heart', 'family_hypertension', 'family_mental'].map((key) => (
          <label key={key} className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={!!form[key]} onChange={(event) => setValue(key, event.target.checked)} />
            {key.replace('family_', '').replace('_', ' ')}
          </label>
        ))}
      </Section>
      <Section title="Medical Contacts" open={open.contacts} toggle={() => setOpen((previous) => ({ ...previous, contacts: !previous.contacts }))}>
        {fields.contacts.map(([key, label]) => (
          <div key={key}>
            <label className="text-xs text-slate-500">{label}</label>
            <input type="text" value={form[key] ?? ''} onChange={(event) => setValue(key, event.target.value)} className={inputClass} />
          </div>
        ))}
      </Section>
      <button onClick={save} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-6 py-2.5 font-medium transition w-full md:w-auto mt-4">Save</button>
    </div>
  );
}
