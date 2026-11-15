import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { api } from './api';
import { useAuth } from './App';
import OccupancyReport from './OccupancyReport';
import { dateLabel, Feedback, Field, Status, useData } from './ui';

const zone = 'Europe/Warsaw';
const part = (value, options) => new Intl.DateTimeFormat('pl-PL', { timeZone: zone, ...options }).format(new Date(value));
const sameDay = (a, b) => part(a, { dateStyle: 'short' }) === part(b, { dateStyle: 'short' });
function rangeLabel(start, end) {
  if (!sameDay(start, end)) return `${dateLabel(start)} – ${dateLabel(end)}`;
  const day = part(start, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  return `${day.charAt(0).toUpperCase()}${day.slice(1)}, ${part(start, { timeStyle: 'short' })}–${part(end, { timeStyle: 'short' })}`;
}

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
  const room = id => state.data?.rooms.find(value => value.id === id);
  const roomName = id => room(id)?.name || `Sala #${id}`;
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

  function cards(items, emptyText = 'Brak rezerwacji do wyświetlenia.') {
    if (!items.length) return <div className="list-empty"><i className="pi pi-inbox" aria-hidden="true" /><span>{emptyText}</span></div>;
    return <div className="booking-list">{items.map(item => { const place = room(item.room_id);
      return <article className={`booking-card status-${item.status}`} key={item.id}>
        <div className="booking-date" aria-hidden="true"><span className="booking-day">{part(item.start, { day: 'numeric' })}</span><span className="booking-month">{part(item.start, { month: 'short' }).replace('.', '')}</span></div>
        <div className="booking-body">
          <div className="booking-top"><h3>{item.title}</h3><Status value={item.status} /></div>
          <p className="booking-meta">
            <span><i className="pi pi-clock" aria-hidden="true" /> {rangeLabel(item.start, item.end)}</span>
            <span><i className="pi pi-map-marker" aria-hidden="true" /> {roomName(item.room_id)}{place?.building ? `, ${place.building}` : ''}</span>
            {guardian && <span><i className="pi pi-user" aria-hidden="true" /> Wnioskodawca: użytkownik #{item.user_id}</span>}
          </p>
          {item.note && <p className="booking-note"><i className="pi pi-comment" aria-hidden="true" /> {item.note}</p>}
          {item.decision_comment && <p className="booking-decision"><strong>Uzasadnienie:</strong> {item.decision_comment}</p>}
        </div>
        <div className="booking-actions">
          {guardian && item.status === 'pending' && <Button label="Rozpatrz wniosek" icon="pi pi-check-square" size="small" onClick={() => { setSelected(item); setComment(''); setError(''); }} />}
          {!guardian && ['pending', 'approved'].includes(item.status) && <Button label="Anuluj" icon="pi pi-times" size="small" severity="danger" outlined disabled={busy} onClick={() => cancel(item)} />}
          <Link className="ghost-link" to={`/calendar/${item.room_id}`}><i className="pi pi-calendar" aria-hidden="true" /> Kalendarz sali</Link>
        </div>
      </article>; })}</div>;
  }

  const myRooms = state.data?.rooms.filter(value => assignedIds.includes(value.id)) || [];
  const roomList = myRooms.length ? <div className="room-grid compact">{myRooms.map(value => { const waiting = pending.filter(item => item.room_id === value.id).length;
    return <article className="room-card" key={value.id}>
      <div className="room-icon" aria-hidden="true"><i className="pi pi-building" /></div>
      <div className="room-body"><h3>{value.name}</h3>
        <p className="room-meta"><span><i className="pi pi-map-marker" aria-hidden="true" /> {value.building || 'Budynek nieokreślony'}</span><span><i className="pi pi-users" aria-hidden="true" /> {value.capacity} miejsc</span></p>
        <span className={`pending-badge ${waiting ? 'has' : ''}`}><i className={`pi ${waiting ? 'pi-bell' : 'pi-check-circle'}`} aria-hidden="true" /> {waiting ? `Oczekujące wnioski: ${waiting}` : 'Brak oczekujących wniosków'}</span>
      </div>
      <Link className="p-button p-button-rounded calendar-btn" to={`/calendar/${value.id}`}><i className="pi pi-calendar" aria-hidden="true" /> Kalendarz</Link>
    </article>; })}</div> : <div className="list-empty"><i className="pi pi-building" aria-hidden="true" /><span>Nie masz przypisanych sal.</span></div>;

  const tabs = [['summary', 'pi-home', 'Podsumowanie'], ['rooms', 'pi-building', 'Twoje sale', myRooms.length], ['pending', 'pi-inbox', 'Zgłoszenia', pending.length], ['history', 'pi-history', 'Historia'], ['report', 'pi-chart-bar', 'Raport zajętości']];
  return <main className="wide-page"><h1>{guardian ? 'Panel opiekuna sal' : 'Moje rezerwacje'}</h1><Feedback {...state} />{notice && <Message severity="success" text={notice} />}<Feedback error={!selected ? error : ''} />
    {state.data && (guardian ? <div className="dashboard-layout"><nav className="surface sidebar" aria-label="Panel opiekuna"><span className="eyebrow">Panel opiekuna</span>
        {tabs.map(([value, icon, label, count]) => <button type="button" key={value} className={`side-tab ${tab === value ? 'active' : ''}`} aria-current={tab === value ? 'page' : undefined} onClick={() => setTab(value)}><i className={`pi ${icon}`} aria-hidden="true" /><span>{label}</span>{count > 0 && <span className="side-count">{count}</span>}</button>)}
      </nav><div className="surface dashboard-main">
      {tab === 'summary' && <><div className="panel-heading"><h2>Podsumowanie</h2></div><div className="metrics"><Metric label="Twoje sale" value={assignedIds.length} icon="building" /><Metric label="Oczekujące wnioski" value={pending.length} icon="inbox" /><Metric label="Historia rezerwacji" value={history.length} icon="history" /></div><div className="panel-heading"><h2>Najnowsze zgłoszenia</h2></div>{cards(pending, 'Brak nowych zgłoszeń.')}</>}
      {tab === 'rooms' && <><div className="panel-heading"><h2>Twoje sale</h2><span className="panel-count">{myRooms.length}</span></div>{roomList}</>}
      {tab === 'pending' && <><div className="panel-heading"><h2>Oczekujące zgłoszenia</h2><span className="panel-count">{pending.length}</span></div>{cards(pending, 'Brak oczekujących zgłoszeń.')}</>}
      {tab === 'history' && <><div className="panel-heading"><h2>Historia rezerwacji</h2><span className="panel-count">{history.length}</span></div>{state.data.decisions.filter(item => !item.applied).map(item => <Message key={item.id} severity={item.blocked ? 'error' : 'warn'} text={`Decyzja dla wniosku #${item.reservation_id}: ${item.blocked ? 'konflikt — wymaga sprawdzenia' : 'oczekuje na przekazanie'}`} />)}{cards(history)}</>}
      {tab === 'report' && <OccupancyReport description="Procent czasu rezerwacji (07:00–22:00), który w wybranym okresie zajmują zatwierdzone rezerwacje w Twoich salach." />}
    </div></div> : <section className="surface"><div className="panel-heading"><h2>Oczekujące wnioski</h2><span className="panel-count">{pending.length}</span></div>{cards(pending, 'Nie masz oczekujących wniosków.')}<div className="panel-heading spaced"><h2>Pozostałe rezerwacje</h2><span className="panel-count">{history.length}</span></div>{cards(history)}</section>)}
    <Dialog header="Rozpatrz wniosek" visible={!!selected} modal onHide={() => { if (!busy) setSelected(null); }} style={{ width: '32rem' }} breakpoints={{ '600px': '95vw' }}>{selected && <div className="form-stack"><div className="decision-summary"><h3>{selected.title}</h3><p><i className="pi pi-map-marker" aria-hidden="true" /> {roomName(selected.room_id)}</p><p><i className="pi pi-clock" aria-hidden="true" /> {rangeLabel(selected.start, selected.end)}</p>{selected.note && <p><i className="pi pi-comment" aria-hidden="true" /> {selected.note}</p>}</div><Field label="Komentarz (wymagany przy odrzuceniu)"><InputTextarea rows={4} value={comment} onChange={e => setComment(e.target.value)} /></Field><Feedback error={error} /><div className="button-row"><Button label="Zatwierdź" icon="pi pi-check" severity="success" disabled={busy} onClick={() => decide('approved')} /><Button label="Odrzuć" icon="pi pi-times" severity="danger" outlined disabled={busy} onClick={() => decide('rejected')} /></div></div>}</Dialog>
  </main>;
}
export function Metric({ label, value, icon }) { return <div className="metric"><i className={`pi pi-${icon}`} /><strong>{value}</strong><span>{label}</span></div>; }
