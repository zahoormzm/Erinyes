import { useEffect, useState } from 'react';
import { createFamily, getFamily, joinFamily } from '../api';
import FamilyDashboard from '../components/FamilyDashboard';
import useStore from '../store';

export default function Family() {
  const { profile, selectedUserId, setProfile, showToast } = useStore();
  const [family, setFamily] = useState(null);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [relationship, setRelationship] = useState('Sibling');
  const [privacy, setPrivacy] = useState('summary');

  useEffect(() => {
    if (!profile?.family_id) return;
    (async () => {
      try {
        const response = await getFamily(profile.family_id);
        setFamily(response.data);
      } catch (error) {
        showToast(error.message, 'error');
      }
    })();
  }, [profile?.family_id, showToast]);

  if (profile?.family_id && family) {
    return <FamilyDashboard data={family} />;
  }

  return (
    <div className="glass-card p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="glass-subcard p-5">
          <div className="font-semibold text-slate-900 mb-4">Create a Family</div>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Family name" className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-full" />
          <button onClick={async () => { try { const response = await createFamily(name, selectedUserId); setFamily({ family: response.data, members: [], health_flags: [] }); setProfile({ ...(profile || {}), family_id: response.data.id }); showToast('Family created'); } catch (error) { showToast(error.message, 'error'); } }} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition mt-3">Create</button>
        </div>
        <div className="glass-subcard p-5">
          <div className="font-semibold text-slate-900 mb-4">Join a Family</div>
          <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="Join code" className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-full mb-3" />
          <select value={relationship} onChange={(event) => setRelationship(event.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-full mb-3">
            {['Father', 'Mother', 'Sibling', 'Spouse', 'Child', 'Other'].map((option) => <option key={option}>{option}</option>)}
          </select>
          <select value={privacy} onChange={(event) => setPrivacy(event.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-full mb-3">
            <option value="full">Full</option>
            <option value="summary">Summary</option>
            <option value="minimal">Minimal</option>
          </select>
          <button onClick={async () => { try { const response = await joinFamily(code, selectedUserId, relationship, privacy); setFamily({ family: response.data, members: [], health_flags: [] }); setProfile({ ...(profile || {}), family_id: response.data.id }); showToast('Joined family'); } catch (error) { showToast(error.message, 'error'); } }} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition">Join</button>
        </div>
      </div>
    </div>
  );
}
