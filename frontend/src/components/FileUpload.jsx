import { FileText, Upload } from 'lucide-react';
import { useRef, useState } from 'react';
import useStore from '../store';

export default function FileUpload({ onUpload, accept, label, endpoint, disabled = false, disabledMessage = '' }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { showToast } = useStore();

  const upload = async () => {
    if (!file) return;
    try {
      setLoading(true);
      setError('');
      const response = await endpoint(file);
      onUpload(response.data);
      showToast(`${label} processed successfully`);
    } catch (uploadError) {
      setError(uploadError.message);
      showToast(uploadError.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div
        onClick={() => { if (!disabled) inputRef.current?.click(); }}
        onDragOver={(event) => { if (disabled) return; event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          if (disabled) return;
          event.preventDefault();
          setDragging(false);
          setFile(event.dataTransfer.files[0]);
        }}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition ${disabled ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-70' : dragging ? 'cursor-pointer border-emerald-500 bg-emerald-50' : 'cursor-pointer border-slate-300 hover:border-slate-400'}`}
      >
        <Upload className="mx-auto text-slate-300" size={48} />
        <div className="text-sm text-slate-500 mt-3">
          {disabled ? disabledMessage || 'This uploader is disabled right now.' : 'Drag and drop your file here, or click to browse'}
        </div>
        <div className="text-xs text-slate-400 mt-1">Accepted: {accept}</div>
        <input ref={inputRef} type="file" accept={accept} hidden disabled={disabled} onChange={(event) => setFile(event.target.files?.[0] || null)} />
      </div>
      {file && (
        <div className="mt-4">
          <div className="flex items-center gap-2 text-sm text-slate-700">
            <FileText size={16} />
            <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
          <button onClick={upload} disabled={loading} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg px-4 py-2 font-medium transition mt-3 disabled:opacity-60">
            {loading ? 'Processing...' : 'Upload'}
          </button>
        </div>
      )}
      {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
    </div>
  );
}
