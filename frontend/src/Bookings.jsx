import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { api } from './api';
import { useAuth } from './App';
import { dateLabel, Feedback, Field, Status, useData } from './ui';

export default function Bookings({ guardian = false }) {
  const { user } = useAuth(); const [tab, setTab] = useState('summary'); const [selected, setSelected] = useState(null); const [comment, setComment] = useState(''); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false);
  const state = useData(async () => {
    const [rooms, reservations, assignments, decisions] = await Promise.all([api('rooms/'), api('reservations/'), guardian ? api('guardians/mine/') : [], guardian ? api('decisions/') : []]);
    return { rooms, reservations, assignments, decisions };
  }, [user.id, guardian]);
  const assignedIds = state.data?.assignments.map(item => item.room_id) || [];
  const bookings = state.data?.reservations.filter(item => guardian ? assignedIds.includes(item.room_id) : item.user_id === user.id) || [];
  const pending = bookings.filter(item => item.status === 'pending');
  const history = bookings.filter(item => item.status !== 'pending');
  const roomName = id => state.data?.rooms.find(room => room.id === id)?.name || `Sala #${id}`;
  async function decide(status) {
    if (status === 'rejected' && !comment.trim()) { setError('Podaj uzasadnienie odrzucenia wniosku.'); return; }
    setBusy(true); setError('');
    try { const result = await api('decisions/', { method: 'POST', body: { reservation_id: selected.id, status, comment } }); setSelected(null);
      setNotice(result.status === 'pending_retry' ? 'Decyzja została zapisana i oczekuje na przekazanie do rezerwacji.' : 'Decyzja została zapisana.'); state.reload();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function cancel(item) {
    if (!window.confirm('Czy anulować tę rezerwację?')) return;
    setBusy(true); setError('');
    try { await api(`reservations/${item.id}/`, { method: 'DELETE' }); setNotice('Rezerwacja została anulowana.'); state.reload(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  function cards(items) {
    return items.length ? items.map(item => <article className="booking-card" key={item.id}><div className="section-heading"><h3>{item.title}</h3><Status value={item.status} /></div><p><strong>{roomName(item.room_id)}</strong> · {dateLabel(item.start)} – {dateLabel(item.end)}</p>{guardian && <p className="muted">Wnioskodawca: użytkownik #{item.user_id}</p>}{item.note && <p>{item.note}</p>}{item.decision_comment && <p><strong>Uzasadnienie:</strong> {item.decision_comment}</p>}<div className="button-row"><Link to={`/calendar/${item.room_id}`}>Kalendarz sali <i className="pi pi-arrow-right" /></Link>{guardian && item.status === 'pending' && <Button label="Rozpatrz wniosek" onClick={() => { setSelected(item); setComment(''); setError(''); }} />}{!guardian && ['pending', 'approved'].includes(item.status) && <Button label="Anuluj" severity="danger" outlined disabled={busy} onClick={() => cancel(item)} />}</div></article>) : <p className="empty">Brak rezerwacji do wyświetlenia.</p>;
  }
  return <main className="wide-page"><h1>{guardian ? 'Panel opiekuna sal' : 'Moje rezerwacje'}</h1><Feedback {...state} />{notice && <Message severity="success" text={notice} />}<Feedback error={!selected ? error : ''} />
    {state.data && (guardian ? <div className="dashboard-layout"><aside className="surface sidebar"><span className="eyebrow">Panel opiekuna</span>{[['summary', 'pi-chart-bar', 'Podsumowanie'], ['rooms', 'pi-building', 'Twoje sale'], ['pending', 'pi-inbox', `Zgłoszenia (${pending.length})`], ['history', 'pi-history', 'Historia']].map(([value, icon, label]) => <Button key={value} text={tab !== value} label={label} icon={`pi ${icon}`} onClick={() => setTab(value)} />)}</aside><div className="surface dashboard-main">
      {tab === 'summary' && <><h2>Podsumowanie</h2><div className="metrics"><Metric label="Twoje sale" value={assignedIds.length} icon="building" /><Metric label="Oczekujące wnioski" value={pending.length} icon="inbox" /><Metric label="Historia rezerwacji" value={history.length} icon="history" /></div><h2>Najnowsze zgłoszenia</h2>{cards(pending)}</>}
      {tab === 'rooms' && <><h2>Twoje sale</h2>{state.data.rooms.filter(room => assignedIds.includes(room.id)).map(room => <article className="booking-card section-heading" key={room.id}><div><h3>{room.name}</h3><p className="muted">{room.building} · {room.capacity} miejsc</p></div><Link className="p-button" to={`/calendar/${room.id}`}>Kalendarz</Link></article>)}{!assignedIds.length && <p>Nie masz przypisanych sal.</p>}</>}
      {tab === 'pending' && <><h2>Oczekujące zgłoszenia</h2>{cards(pending)}</>}
      {tab === 'history' && <><h2>Historia rezerwacji</h2>{cards(history)}{state.data.decisions.filter(item => !item.applied).map(item => <Message key={item.id} severity={item.blocked ? 'error' : 'warn'} text={`Decyzja dla wniosku #${item.reservation_id}: ${item.blocked ? 'konflikt — wymaga sprawdzenia' : 'oczekuje na przekazanie'}`} />)}</>}
    </div></div> : <section className="surface"><h2>Oczekujące wnioski</h2>{cards(pending)}<h2>Pozostałe rezerwacje</h2>{cards(history)}</section>)}
    <Dialog header="Rozpatrz wniosek" visible={!!selected} modal onHide={() => { if (!busy) setSelected(null); }} style={{ width: '32rem' }} breakpoints={{ '600px': '95vw' }}>{selected && <div className="form-stack"><h3>{selected.title}</h3><p>{roomName(selected.room_id)} · {dateLabel(selected.start)} – {dateLabel(selected.end)}</p>{selected.note && <p>{selected.note}</p>}<Field label="Komentarz (wymagany przy odrzuceniu)"><InputTextarea rows={4} value={comment} onChange={e => setComment(e.target.value)} /></Field><Feedback error={error} /><div className="button-row"><Button label="Zatwierdź" icon="pi pi-check" severity="success" disabled={busy} onClick={() => decide('approved')} /><Button label="Odrzuć" icon="pi pi-times" severity="danger" disabled={busy} onClick={() => decide('rejected')} /></div></div>}</Dialog>
  </main>;
}
export function Metric({ label, value, icon }) { return <div className="metric"><i className={`pi pi-${icon}`} /><strong>{value}</strong><span>{label}</span></div>; }
