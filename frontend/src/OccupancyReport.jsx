import { useEffect, useState } from 'react';
import { DateTime } from 'luxon';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { InputText } from 'primereact/inputtext';
import { api } from './api';
import { Feedback, Field } from './ui';

const zone = 'Europe/Warsaw';
const WEEKDAYS = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela'];
const iso = value => value.toISODate();
const number = (value, digits = 1) => new Intl.NumberFormat('pl-PL', { maximumFractionDigits: digits }).format(value);
const hours = value => `${number(value)} h`;
const percent = value => `${number(value)}%`;

function presets() {
  const today = DateTime.now().setZone(zone).startOf('day');
  const lastMonth = today.minus({ months: 1 });
  return [
    ['week', 'Ten tydzień', today.startOf('week'), today.endOf('week')],
    ['month', 'Ten miesiąc', today.startOf('month'), today.endOf('month')],
    ['previous', 'Poprzedni miesiąc', lastMonth.startOf('month'), lastMonth.endOf('month')],
    ['last30', 'Ostatnie 30 dni', today.minus({ days: 29 }), today],
    ['semester', 'Najbliższe 3 miesiące', today, today.plus({ months: 3 }).minus({ days: 1 })],
  ].map(([key, label, start, end]) => ({ key, label, start: iso(start), end: iso(end) }));
}

function Bar({ label, sub, approved, pending, detail }) {
  return <div className="occ-row">
    <div className="occ-label"><strong>{label}</strong>{sub && <span>{sub}</span>}</div>
    <div className="occ-track" role="img" aria-label={`${label}: zajętość ${percent(approved)}${pending ? `, oczekujące ${percent(pending)}` : ''}`}>
      {approved > 0 && <span className="occ-fill approved" style={{ width: `${Math.min(approved, 100)}%` }} />}
      {pending > 0 && <span className="occ-fill pending" style={{ width: `${Math.min(pending, 100 - Math.min(approved, 100))}%` }} />}
      <span className="occ-tip" role="tooltip"><strong>{label}</strong>{detail}</span>
    </div>
    <div className="occ-value">{percent(approved)}</div>
  </div>;
}

function downloadCsv(report) {
  const decimal = value => String(value).replace('.', ',');
  const rows = [
    ['Raport zajętości sal', `${report.start} – ${report.end}`],
    ['Dni w raporcie', report.day_count, report.workdays_only ? 'tylko dni robocze' : 'wszystkie dni', `godziny ${report.hours_per_day} h/dzień (07:00–22:00)`],
    [],
    ['Sala', 'Budynek', 'Miejsca', 'Dostępne godziny', 'Zarezerwowane godziny (zatwierdzone)', 'Oczekujące godziny', 'Liczba rezerwacji', 'Zajętość %', 'Oczekujące %'],
    ...report.rooms.map(room => [room.name, room.building, room.capacity, room.available_hours, decimal(room.approved_hours), decimal(room.pending_hours), room.reservation_count, decimal(room.occupancy), decimal(room.pending_share)]),
    ['RAZEM', '', '', report.total.available_hours, decimal(report.total.approved_hours), decimal(report.total.pending_hours), report.total.reservation_count, decimal(report.total.occupancy), decimal(report.total.pending_share)],
    [],
    ['Dzień tygodnia', 'Dostępne godziny', 'Zarezerwowane godziny', 'Zajętość %'],
    ...report.by_weekday.map(day => [WEEKDAYS[day.weekday], day.available_hours, decimal(day.approved_hours), decimal(day.occupancy)]),
  ];
  const csv = rows.map(row => row.map(cell => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(';')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }));
  const link = Object.assign(document.createElement('a'), { href: url, download: `raport-zajetosci-${report.start}_${report.end}.csv` });
  document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
}

export default function OccupancyReport({ title = 'Raport zajętości sal', description }) {
  const options = presets();
  const [range, setRange] = useState({ start: options[1].start, end: options[1].end, workdays: false });
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const active = options.find(item => item.start === range.start && item.end === range.end)?.key;

  async function generate(next = range) {
    if (!next.start || !next.end) { setError('Wybierz datę początkową i końcową.'); return; }
    if (next.end < next.start) { setError('Data końcowa nie może być wcześniejsza niż początkowa.'); return; }
    setBusy(true); setError('');
    try {
      const params = new URLSearchParams({ start: next.start, end: next.end, ...(next.workdays ? { workdays: '1' } : {}) });
      setReport(await api(`reports/occupancy/?${params}`));
    } catch (err) { setError(err.message); setReport(null); }
    finally { setBusy(false); }
  }
  useEffect(() => { generate(); }, []);
  function choose(item) { const next = { ...range, start: item.start, end: item.end }; setRange(next); generate(next); }

  const label = report && `${DateTime.fromISO(report.start).setLocale('pl').toFormat('d MMMM yyyy')} – ${DateTime.fromISO(report.end).setLocale('pl').toFormat('d MMMM yyyy')}`;
  return <section className="occupancy" aria-labelledby="occ-title">
    <div className="panel-heading"><h2 id="occ-title">{title}</h2></div>
    {description && <p className="muted occ-intro">{description}</p>}

    <form className="occ-filters" onSubmit={event => { event.preventDefault(); generate(); }}>
      <div className="occ-presets" role="group" aria-label="Szybki wybór okresu">
        {options.map(item => <button type="button" key={item.key} className={`occ-preset ${active === item.key ? 'active' : ''}`} aria-pressed={active === item.key} onClick={() => choose(item)}>{item.label}</button>)}
      </div>
      <div className="occ-controls">
        <Field label="Od"><InputText type="date" required value={range.start} max={range.end || undefined} onChange={e => setRange({ ...range, start: e.target.value })} /></Field>
        <Field label="Do"><InputText type="date" required value={range.end} min={range.start || undefined} onChange={e => setRange({ ...range, end: e.target.value })} /></Field>
        <label className="check-field occ-check"><Checkbox checked={range.workdays} onChange={e => setRange({ ...range, workdays: e.checked })} /> Tylko dni robocze (pn–pt)</label>
        <div className="occ-buttons">
          <Button type="submit" label="Generuj raport" icon="pi pi-chart-bar" loading={busy} />
          <Button type="button" label="Pobierz CSV" icon="pi pi-download" outlined disabled={!report || busy} onClick={() => downloadCsv(report)} />
        </div>
      </div>
    </form>

    <Feedback error={error} />
    {busy && !report && <Feedback loading />}
    {report && <div className={`occ-result ${busy ? 'is-busy' : ''}`}>
      <p className="occ-period"><i className="pi pi-calendar" aria-hidden="true" /> {label} · {report.day_count} {report.day_count === 1 ? 'dzień' : 'dni'}{report.workdays_only ? ' roboczych' : ''} · godziny rezerwacji 07:00–22:00</p>
      <div className="occ-tiles">
        <div className="occ-tile occ-main"><span>Średnia zajętość</span><strong>{percent(report.total.occupancy)}</strong><small>zatwierdzone rezerwacje / dostępny czas</small></div>
        <div className="occ-tile"><span>Zarezerwowane</span><strong>{hours(report.total.approved_hours)}</strong><small>z {hours(report.total.available_hours)} dostępnych</small></div>
        <div className="occ-tile"><span>Oczekujące wnioski</span><strong>{hours(report.total.pending_hours)}</strong><small>{percent(report.total.pending_share)} czasu, jeszcze niewliczone</small></div>
        <div className="occ-tile"><span>Rezerwacje</span><strong>{report.total.reservation_count}</strong><small>w {report.total.room_count} {report.total.room_count === 1 ? 'sali' : 'salach'}</small></div>
      </div>

      <div className="occ-chart">
        <div className="occ-chart-head"><h3>Zajętość sal</h3>
          <div className="occ-legend"><span><i className="occ-swatch approved" /> Zatwierdzone</span><span><i className="occ-swatch pending" /> Oczekujące (niewliczone do %)</span></div>
        </div>
        {report.rooms.length ? report.rooms.map(room => <Bar key={room.room_id} label={room.name} sub={room.building} approved={room.occupancy} pending={room.pending_share}
          detail={<><span>Zatwierdzone: {hours(room.approved_hours)} ({percent(room.occupancy)})</span><span>Oczekujące: {hours(room.pending_hours)} ({percent(room.pending_share)})</span><span>Dostępne: {hours(room.available_hours)} · rezerwacji: {room.reservation_count}</span></>} />)
          : <div className="list-empty"><i className="pi pi-building" aria-hidden="true" /><span>Brak sal w raporcie.</span></div>}
      </div>

      {report.by_weekday.length > 0 && <div className="occ-chart">
        <div className="occ-chart-head"><h3>Zajętość według dnia tygodnia</h3><span className="muted occ-note">wszystkie sale łącznie, tylko zatwierdzone</span></div>
        {report.by_weekday.map(day => <Bar key={day.weekday} label={WEEKDAYS[day.weekday]} approved={day.occupancy} pending={0}
          detail={<><span>Zarezerwowane: {hours(day.approved_hours)}</span><span>Dostępne: {hours(day.available_hours)}</span></>} />)}
      </div>}

      <details className="occ-table">
        <summary>Pokaż dane w tabeli</summary>
        <div className="occ-table-scroll"><table>
          <thead><tr><th>Sala</th><th>Budynek</th><th>Dostępne</th><th>Zatwierdzone</th><th>Oczekujące</th><th>Rezerwacje</th><th>Zajętość</th></tr></thead>
          <tbody>{report.rooms.map(room => <tr key={room.room_id}><td>{room.name}</td><td>{room.building || '—'}</td><td>{hours(room.available_hours)}</td><td>{hours(room.approved_hours)}</td><td>{hours(room.pending_hours)}</td><td>{room.reservation_count}</td><td><strong>{percent(room.occupancy)}</strong></td></tr>)}</tbody>
          <tfoot><tr><td>Razem</td><td /><td>{hours(report.total.available_hours)}</td><td>{hours(report.total.approved_hours)}</td><td>{hours(report.total.pending_hours)}</td><td>{report.total.reservation_count}</td><td><strong>{percent(report.total.occupancy)}</strong></td></tr></tfoot>
        </table></div>
      </details>
    </div>}
  </section>;
}
