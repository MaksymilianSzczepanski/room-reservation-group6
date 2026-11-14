import { useEffect, useState } from 'react';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Tag } from 'primereact/tag';
export function useData(loader, dependencies = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const [version, setVersion] = useState(0);
  useEffect(() => { let active = true; setState({ data: null, loading: true, error: '' });
    loader().then(data => { if (active) setState({ data, loading: false, error: '' }); })
      .catch(error => { if (active) setState({ data: null, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [...dependencies, version]);
  return { ...state, reload: () => setVersion(value => value + 1) };
}
export function Feedback({ loading, error }) { return <>{loading && <div className="loading" role="status" aria-label="Ładowanie"><ProgressSpinner style={{ width: 36, height: 36 }} /></div>}{error && <Message severity="error" text={error} />}</>; }
export const statusLabels = { pending: 'Oczekuje', approved: 'Zatwierdzona', rejected: 'Odrzucona', cancelled: 'Anulowana' };
export function Status({ value }) { return <Tag value={statusLabels[value] || value} severity={{ pending: 'warning', approved: 'success', rejected: 'danger', cancelled: 'secondary' }[value]} />; }
export const dateLabel = value => new Intl.DateTimeFormat('pl-PL', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Warsaw' }).format(new Date(value));
export function Field({ label, children }) { return <label className="form-field"><span>{label}</span>{children}</label>; }
