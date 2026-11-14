import { useState } from 'react';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { MultiSelect } from 'primereact/multiselect';
import { TabPanel, TabView } from 'primereact/tabview';
import { Message } from 'primereact/message';
import { api } from './api';
import { dateLabel, Feedback, Field, useData } from './ui';
import { Metric } from './Bookings';

export default function Admin({ onAssignmentsChanged }) {
  const [edit, setEdit] = useState(null); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false);
  const state = useData(async () => {
    const [rooms, users, guardians, attributes, reports, notifications] = await Promise.all(['rooms/', 'users/', 'guardians/', 'rooms/attributes/', 'reports/', 'notifications/'].map(path => api(path)));
    return { rooms, users, guardians, attributes, reports, notifications };
  });
  function open(type, value = {}) { setError(''); setEdit({ type, values: { ...value, ...(type === 'rooms' ? { attribute_ids: value.attributes?.map(attr => attr.id) || [] } : {}) } }); }
  const change = (key, value) => setEdit({ ...edit, values: { ...edit.values, [key]: value } });
  function refresh() { state.reload(); onAssignmentsChanged(); }
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { type, values } = edit; const body = { ...values };
      delete body.id; delete body.attributes;
      if (type === 'rooms') body.capacity = Number(body.capacity);
      if (type === 'users') { body.is_student = !!body.is_student; body[values.id ? 'is_staff' : 'is_admin'] = !!body.is_admin; if (values.id) delete body.is_admin; }
      await api(`${type}/${values.id ? `${values.id}/` : ''}`, { method: values.id ? 'PATCH' : 'POST', body });
      setEdit(null); setNotice('Zmiany zostały zapisane.'); refresh();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function remove(type, item) {
    if (!window.confirm(type === 'users' ? 'Czy dezaktywować to konto?' : 'Czy usunąć ten element?')) return;
    setBusy(true); setError('');
    try { await api(`${type}/${item.id}/`, { method: 'DELETE' }); setNotice('Operacja zakończona.'); refresh(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  const table = (items, columns, actions) => <DataTable value={items} paginator rows={10} emptyMessage="Brak danych" size="small" tableStyle={{ minWidth: '32rem' }}>{columns.map(([field, header, body]) => <Column key={field} field={field} header={header} body={body} />)}{actions && <Column header="Operacje" body={actions} />}</DataTable>;
  const editButtons = type => row => <div className="button-row"><Button icon="pi pi-pencil" text aria-label={`Edytuj ${row.name || row.username}`} onClick={() => open(type, row)} /><Button icon="pi pi-trash" severity="danger" text disabled={busy} aria-label={`Usuń ${row.name || row.username}`} onClick={() => remove(type, row)} /></div>;
  const data = state.data;
  return <main className="wide-page"><h1>Administracja</h1><Feedback {...state} />{notice && <Message severity="success" text={notice} />}<Feedback error={!edit ? error : ''} />{state.error && <Button label="Ponów pobieranie" onClick={state.reload} />}
    {data && <section className="surface admin-panel"><TabView>
      <TabPanel header="Sale"><div className="section-heading"><h2>Sale</h2><Button label="Dodaj salę" icon="pi pi-plus" onClick={() => open('rooms')} /></div>{table(data.rooms, [['name', 'Nazwa'], ['building', 'Budynek'], ['capacity', 'Miejsca']], editButtons('rooms'))}</TabPanel>
      <TabPanel header="Użytkownicy"><div className="section-heading"><h2>Użytkownicy</h2><Button label="Dodaj użytkownika" icon="pi pi-user-plus" onClick={() => open('users')} /></div>{table(data.users, [['username', 'Login'], ['email', 'E-mail'], ['is_active', 'Aktywny', row => row.is_active ? 'Tak' : 'Nie'], ['is_admin', 'Rola', row => row.is_admin ? 'Administrator' : row.is_student ? 'Student' : 'Pracownik']], editButtons('users'))}</TabPanel>
      <TabPanel header="Opiekunowie"><div className="section-heading"><h2>Przypisania opiekunów</h2><Button label="Przypisz opiekuna" icon="pi pi-plus" onClick={() => open('guardians')} /></div>{table(data.guardians, [['room_id', 'Sala', row => data.rooms.find(room => room.id === row.room_id)?.name || `#${row.room_id}`], ['user_id', 'Opiekun', row => data.users.find(user => user.id === row.user_id)?.username || `#${row.user_id}`]], row => <Button label="Usuń przypisanie" severity="danger" text disabled={busy} onClick={() => remove('guardians', row)} />)}</TabPanel>
      <TabPanel header="Wyposażenie"><div className="section-heading"><h2>Wyposażenie sal</h2><Button label="Dodaj wyposażenie" icon="pi pi-plus" onClick={() => open('rooms/attributes')} /></div>{table(data.attributes, [['name', 'Nazwa']])}</TabPanel>
      <TabPanel header="Raporty"><h2>Raport rezerwacji</h2><div className="metrics"><Metric label="Sale" value={data.reports.room_count} icon="building" /><Metric label="Wszystkie rezerwacje" value={data.reports.reservation_count} icon="calendar" /><Metric label="Oczekujące" value={data.reports.status_counts.pending || 0} icon="inbox" /></div>{table(data.reports.approved_by_room, [['room_name', 'Sala'], ['count', 'Zatwierdzone rezerwacje']])}</TabPanel>
      <TabPanel header="Powiadomienia"><h2>Historia powiadomień</h2>{table(data.notifications, [['recipient', 'Odbiorca'], ['subject', 'Temat'], ['state', 'Wysyłka', row => row.state === 'sent' ? 'Wysłano' : 'Błąd'], ['created_at', 'Data', row => dateLabel(row.created_at)]])}</TabPanel>
    </TabView></section>}
    <Dialog header={edit?.values.id ? 'Edytuj dane' : 'Dodaj dane'} visible={!!edit} modal onHide={() => { if (!busy) setEdit(null); }} style={{ width: '32rem' }} breakpoints={{ '600px': '95vw' }}>
      {edit && <form className="form-stack" onSubmit={submit}>
        {edit.type === 'rooms' && <><Field label="Nazwa sali"><InputText autoFocus required value={edit.values.name || ''} onChange={e => change('name', e.target.value)} /></Field><Field label="Budynek"><InputText value={edit.values.building || ''} onChange={e => change('building', e.target.value)} /></Field><Field label="Liczba miejsc"><InputText type="number" min="1" required value={edit.values.capacity ?? ''} onChange={e => change('capacity', e.target.value)} /></Field><Field label="Opis"><InputTextarea rows={3} value={edit.values.description || ''} onChange={e => change('description', e.target.value)} /></Field><Field label="Wyposażenie"><MultiSelect value={edit.values.attribute_ids} options={data.attributes} optionLabel="name" optionValue="id" onChange={e => change('attribute_ids', e.value)} /></Field></>}
        {edit.type === 'users' && <><Field label="Login"><InputText required disabled={!!edit.values.id} value={edit.values.username || ''} onChange={e => change('username', e.target.value)} /></Field><Field label={edit.values.id ? 'Nowe hasło (opcjonalne)' : 'Hasło'}><InputText type="password" autoComplete="new-password" required={!edit.values.id} value={edit.values.password || ''} onChange={e => change('password', e.target.value)} /></Field><Field label="E-mail"><InputText type="email" value={edit.values.email || ''} onChange={e => change('email', e.target.value)} /></Field>{[['is_admin', 'Administrator'], ['is_student', 'Student'], ...(edit.values.id ? [['is_active', 'Konto aktywne']] : [])].map(([key, label]) => <label className="check-field" key={key}><Checkbox checked={!!edit.values[key]} onChange={e => change(key, e.checked)} />{label}</label>)}</>}
        {edit.type === 'guardians' && <><Field label="Sala"><Dropdown required value={edit.values.room_id} options={data.rooms} optionLabel="name" optionValue="id" onChange={e => change('room_id', e.value)} placeholder="Wybierz salę" /></Field><Field label="Opiekun"><Dropdown required value={edit.values.user_id} options={data.users.filter(user => user.is_active && !user.is_student)} optionLabel="username" optionValue="id" onChange={e => change('user_id', e.value)} placeholder="Wybierz użytkownika" /></Field></>}
        {edit.type === 'rooms/attributes' && <Field label="Nazwa wyposażenia"><InputText required value={edit.values.name || ''} onChange={e => change('name', e.target.value)} /></Field>}
        <Feedback error={error} /><Button type="submit" label="Zapisz" loading={busy} />
      </form>}
    </Dialog>
  </main>;
}
