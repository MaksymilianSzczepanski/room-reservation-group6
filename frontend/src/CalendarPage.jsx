import { useCallback, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import luxonPlugin from '@fullcalendar/luxon3';
import pl from '@fullcalendar/core/locales/pl';
import { DateTime } from 'luxon';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { api } from './api';
import { useAuth } from './App';
import { dateLabel, Feedback, Field, Status, useData } from './ui';

const zone = 'Europe/Warsaw';
const localInput = value => value.toFormat("yyyy-MM-dd'T'HH:mm");
export default function CalendarPage() {
  const { roomId } = useParams(); const navigate = useNavigate(); const { user, openLogin } = useAuth(); const calendar = useRef();
  const room = useData(() => api(`rooms/${roomId}/`), [roomId]);
  const rooms = useData(() => api('rooms/'));
  const own = useData(() => user ? api(`reservations/?room_id=${roomId}`) : Promise.resolve([]), [user?.id, roomId]);
  const [form, setForm] = useState(null); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false); const [selected, setSelected] = useState(null);
  const canBook = user && !user.is_student;
  const events = useCallback((range, success, failure) => {
    api(`reservations/calendar/?${new URLSearchParams({ room_id: roomId, start: range.startStr, end: range.endStr })}`)
      .then(items => { setError(''); success(items.map(item => ({ ...item, title: item.status === 'pending' ? 'Oczekuje na decyzję' : 'Zarezerwowana', color: item.status === 'pending' ? '#d97706' : '#16865d' }))); })
      .catch(err => { setError(err.message); failure(err); });
  }, [roomId]);
  function startBooking(range) {
    if (!user) { openLogin(actor => { if (!actor.is_student) showBookingForm(range); }); return; }
    if (canBook) showBookingForm(range);
  }
  function showBookingForm(range) {
    let start, end;
    if (range && !range.allDay) {
      start = DateTime.fromISO(range.startStr, { zone }); end = DateTime.fromISO(range.endStr, { zone });
    } else {
      const day = range ? DateTime.fromISO(range.startStr, { zone }) : DateTime.now().setZone(zone).plus({ days: 1 });
      start = day.set({ hour: 9, minute: 0, second: 0, millisecond: 0 }); end = start.plus({ hours: 1 });
    }
    setError(''); setForm({ title: '', start: localInput(start), end: localInput(end), note: '' });
  }
  function onSelect(info) { info.view.calendar.unselect(); startBooking(info); }
  function allowSelect(info) {
    const start = DateTime.fromISO(info.startStr, { zone }), end = DateTime.fromISO(info.endStr, { zone });
    return info.allDay ? end.diff(start, 'days').days <= 1 : start.hasSame(end.minus({ milliseconds: 1 }), 'day');
  }
  function refresh() { own.reload(); calendar.current?.getApi().refetchEvents(); }
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const start = DateTime.fromISO(form.start, { zone }), end = DateTime.fromISO(form.end, { zone });
      if (!start.isValid || !end.isValid || end <= start) throw new Error('Koniec rezerwacji musi być późniejszy niż początek.');
      const result = await api('reservations/', { method: 'POST', body: { ...form, room_id: Number(roomId), start: start.toISO(), end: end.toISO() } });
      setForm(null); setNotice(result.notification_status === 'pending_retry' ? 'Wniosek zapisany. Powiadomienie zostanie ponowione.' : 'Wniosek o rezerwację został wysłany do opiekuna.'); refresh();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function cancel() {
    if (!window.confirm('Czy anulować tę rezerwację?')) return;
    setBusy(true); setError('');
    try { await api(`reservations/${selected.id}/`, { method: 'DELETE' }); setSelected(null); setNotice('Rezerwacja została anulowana.'); refresh(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <main className="wide-page"><Link className="back-link" to="/"><i className="pi pi-arrow-left" /> Wróć do wyszukiwarki</Link><h1>Kalendarz rezerwacji</h1>
    <Feedback loading={room.loading} error={room.error || own.error} />
    {room.data && <><section className="surface room-summary"><div><h2>{room.data.name}</h2><p className="muted">{room.data.building} · {room.data.capacity} miejsc</p><div className="room-attrs">{room.data.attributes.map(attr => <span className="small-chip" key={attr.id}>{attr.name}</span>)}</div><p>{room.data.description}</p></div>
      <div className="summary-actions"><Dropdown aria-label="Wybierz salę" value={Number(roomId)} options={rooms.data || [room.data]} optionLabel="name" optionValue="id" onChange={e => navigate(`/calendar/${e.value}`)} />{!user || canBook ? <Button label={user ? 'Zarezerwuj salę' : 'Zaloguj się, aby zarezerwować'} icon="pi pi-plus" onClick={() => startBooking()} /> : <p className="muted">Konto studenta umożliwia przeglądanie kalendarza.</p>}</div></section>
      <p className="calendar-hint">Kalendarz dostępny bez logowania · godziny rezerwacji: 07:00–22:00 · strefa czasu: Warszawa</p>
      {notice && <Message severity="success" text={notice} />}<Feedback error={!form && !selected ? error : ''} />
      <section className="surface calendar-card" aria-label="Kalendarz sali"><div className="legend"><span><i className="dot pending" /> Oczekuje na decyzję</span><span><i className="dot approved" /> Zatwierdzona</span>{(!user || canBook) && <span className="legend-hint"><i className="pi pi-info-circle" /> W widoku tygodnia lub dnia zaznacz myszą godziny, aby zarezerwować. W widoku miesiąca kliknij dzień.</span>}</div>
        <FullCalendar key={roomId} ref={calendar} plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, luxonPlugin]} locale={pl} timeZone={zone} initialView="dayGridMonth" height="auto" firstDay={1} nowIndicator slotMinTime="07:00:00" slotMaxTime="22:00:00" allDaySlot={false} displayEventEnd headerToolbar={{ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }} events={events} selectable={!user || canBook} selectMirror selectOverlap={false} selectAllow={allowSelect} select={onSelect} selectLongPressDelay={300} eventClick={info => { setError(''); setSelected(own.data?.find(item => item.id === Number(info.event.id)) || { ...info.event.extendedProps, start: info.event.start.toISOString(), end: info.event.end.toISOString() }); }} />
      </section></>}
    <Dialog header="Wniosek o rezerwację" visible={!!form} modal onHide={() => { if (!busy) setForm(null); }} style={{ width: '32rem' }} breakpoints={{ '600px': '95vw' }}>
      {form && <form className="form-stack" onSubmit={submit}><p className="muted">{room.data?.name} · jeden dzień, 07:00–22:00 (Warszawa). Wniosek blokuje termin do decyzji lub anulowania.</p>
        <Field label="Tytuł"><InputText autoFocus required maxLength={200} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></Field>
        <Field label="Początek"><InputText type="datetime-local" required value={form.start} onChange={e => setForm({ ...form, start: e.target.value })} /></Field>
        <Field label="Koniec"><InputText type="datetime-local" required value={form.end} onChange={e => setForm({ ...form, end: e.target.value })} /></Field>
        <Field label="Uwagi dla opiekuna"><InputTextarea rows={3} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} /></Field><Feedback error={error} /><Button type="submit" label="Wyślij wniosek" loading={busy} />
      </form>}
    </Dialog>
    <Dialog header={selected?.title || 'Zajęty termin'} visible={!!selected} modal onHide={() => { if (!busy) setSelected(null); }} style={{ width: '30rem' }} breakpoints={{ '600px': '95vw' }}>
      {selected && <div className="form-stack"><Status value={selected.status} /><p>{dateLabel(selected.start)} – {dateLabel(selected.end)}</p>{selected.note && <p>{selected.note}</p>}{selected.decision_comment && <p>Decyzja opiekuna: {selected.decision_comment}</p>}<Feedback error={error} />{user && (user.id === selected.user_id || user.is_admin) && selected.id && ['pending', 'approved'].includes(selected.status) && <Button severity="danger" label="Anuluj rezerwację" loading={busy} onClick={cancel} />}</div>}
    </Dialog>
  </main>;
}
