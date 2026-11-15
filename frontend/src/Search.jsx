import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AutoComplete } from 'primereact/autocomplete';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { api } from './api';
import { Feedback, useData } from './ui';

const empty = { building: '', name: '', minimum: '', maximum: '', attributes: [] };

function toQuery(filters) {
  const params = new URLSearchParams();
  const values = { building__icontains: filters.building.trim(), name__icontains: filters.name.trim(), capacity__gte: filters.minimum, capacity__lte: filters.maximum };
  for (const [key, value] of Object.entries(values)) if (value) params.set(key, value);
  filters.attributes.forEach(id => params.append('attributes__id', id));
  return params.toString();
}

const normalize = value => (value || '').toLocaleLowerCase('pl').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
const matches = (value, text) => normalize(value).includes(normalize(text).trim());
const plural = count => count === 1 ? 'sala' : [2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100) ? 'sale' : 'sal';

function Highlight({ text, query }) {
  const at = query.trim() ? normalize(text).indexOf(normalize(query).trim()) : -1;
  if (at < 0) return text;
  const end = at + query.trim().length;
  return <>{text.slice(0, at)}<mark>{text.slice(at, end)}</mark>{text.slice(end)}</>;
}

function Suggest({ value, onChange, onPick, source, item, placeholder }) {
  const ref = useRef(null);
  const [suggestions, setSuggestions] = useState([]);
  const complete = event => setSuggestions(source(event.query).slice(0, 50));
  return <AutoComplete ref={ref} value={value} suggestions={suggestions} completeMethod={complete} delay={120} placeholder={placeholder}
    itemTemplate={item} panelClassName="suggest-panel" scrollHeight="280px" emptyMessage="Brak podpowiedzi" showEmptyMessage
    onChange={event => onChange(typeof event.value === 'string' ? event.value : '')} onSelect={event => onPick(event.value)}
    onFocus={event => { if (!value) ref.current?.search?.(event, '', 'dropdown'); }} />;
}

export default function Search() {
  const [filters, setFilters] = useState(empty);
  const [query, setQuery] = useState('');
  const rooms = useData(() => api(`search/${query ? `?${query}` : ''}`), [query]);
  const attributes = useData(() => api('rooms/attributes/'));
  const buildings = useData(() => api('rooms/'));

  function run(next) { const value = toQuery(next); if (value === query) rooms.reload(); else setQuery(value); }
  function submit(event) { event.preventDefault(); run(filters); }
  function reset() { setFilters(empty); run(empty); }
  function toggleAttribute(id) {
    const selected = filters.attributes.includes(id) ? filters.attributes.filter(value => value !== id) : [...filters.attributes, id];
    const next = { ...filters, attributes: selected }; setFilters(next); run(next);
  }
  function clearAttributes() { const next = { ...filters, attributes: [] }; setFilters(next); run(next); }
  const field = (key, value) => setFilters({ ...filters, [key]: value });
  const activeCount = ['building', 'name', 'minimum', 'maximum'].filter(key => filters[key]).length + filters.attributes.length;
  const allRooms = buildings.data || [];
  const buildingNames = [...new Set(allRooms.map(room => room.building).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pl'));
  const roomsIn = building => allRooms.filter(room => room.building === building).length;
  function pick(key, value) { const next = { ...filters, [key]: value }; setFilters(next); run(next); }

  return <main className="search-page">
    <div className="logo-container"><img src="/images/logo.png" alt="UniwRersu" /></div>
    <h1 className="subtitle">Wyszukaj salę</h1>
    <p className="lead">Znajdź wolną salę według budynku, liczby miejsc i wyposażenia.</p>

    <form className="search-container" onSubmit={submit} onReset={event => { event.preventDefault(); reset(); }}>
      <label className="search-field"><i className="pi pi-map-marker" /><span>Budynek</span>
        <Suggest placeholder="Wszystkie budynki" value={filters.building} onChange={value => field('building', value)} onPick={value => pick('building', value)}
          source={text => buildingNames.filter(value => matches(value, text))}
          item={value => <><i className="pi pi-building suggest-icon" aria-hidden="true" /><span className="suggest-main"><Highlight text={value} query={filters.building} /></span><span className="suggest-meta">{roomsIn(value)} {plural(roomsIn(value))}</span></>} /></label>
      <label className="search-field"><i className="pi pi-key" /><span>Sala</span>
        <Suggest placeholder="Np. 105" value={filters.name} onChange={value => field('name', value)} onPick={value => pick('name', value)}
          source={text => allRooms.filter(room => !filters.building.trim() || matches(room.building, filters.building)).map(room => room.name).filter(value => matches(value, text))}
          item={value => { const room = allRooms.find(item => item.name === value); return <><i className="pi pi-key suggest-icon" aria-hidden="true" /><span className="suggest-main"><Highlight text={value} query={filters.name} /></span><span className="suggest-meta">{room?.building || '—'} · {room?.capacity} miejsc</span></>; }} /></label>
      <div className="search-field"><i className="pi pi-users" /><span>Liczba miejsc</span><div className="capacity-inputs"><InputText aria-label="Minimalna liczba miejsc" type="number" min="1" placeholder="Od" value={filters.minimum} onChange={e => field('minimum', e.target.value)} /><span className="dash" aria-hidden="true" /><InputText aria-label="Maksymalna liczba miejsc" type="number" min={filters.minimum || 1} placeholder="Do" value={filters.maximum} onChange={e => field('maximum', e.target.value)} /></div></div>
      <div className="search-actions">
        <Button type="submit" label="Szukaj" icon="pi pi-search" rounded className="search-btn" />
        <Button type="reset" label="Reset" icon="pi pi-refresh" rounded outlined className="reset-btn" aria-label="Resetuj filtry" disabled={!activeCount && !query} />
      </div>
    </form>

    <section className="attributes" aria-labelledby="attr-title">
      <div className="attr-header">
        <span className="attr-title" id="attr-title"><i className="pi pi-sliders-h" /> Wyposażenie sali</span>
        {filters.attributes.length > 0 && <><span className="attr-count">Wybrano: {filters.attributes.length}</span><button type="button" className="link-button" onClick={clearAttributes}><i className="pi pi-times" /> Wyczyść wyposażenie</button></>}
      </div>
      <div className="chips" role="group" aria-label="Filtruj według wyposażenia">
        {attributes.data?.map(attr => { const active = filters.attributes.includes(attr.id);
          return <button type="button" className={`chip ${active ? 'active' : ''}`} aria-pressed={active} key={attr.id} onClick={() => toggleAttribute(attr.id)}><i className={`pi ${active ? 'pi-check' : 'pi-plus'}`} />{attr.name}</button>; })}
        {attributes.loading && <span className="chip-placeholder">Ładowanie wyposażenia…</span>}
        {attributes.data?.length === 0 && <span className="chip-placeholder">Brak zdefiniowanego wyposażenia</span>}
      </div>
      {filters.attributes.length > 1 && <p className="attr-hint">Pokazywane są sale, które mają całe wybrane wyposażenie.</p>}
    </section>
    <Feedback error={attributes.error || buildings.error} />

    <section className="results" aria-label="Wyniki wyszukiwania">
      <div className="results-header"><h2>Dostępne sale</h2>{rooms.data && <span className="results-count"><i className="pi pi-list" /> Znaleziono: {rooms.data.length}</span>}</div>
      <Feedback {...rooms} />
      <div className="room-grid">
        {rooms.data?.map(room => <article className="room-card" key={room.id}>
          <div className="room-icon" aria-hidden="true"><i className="pi pi-building" /></div>
          <div className="room-body">
            <h3>{room.name}</h3>
            <p className="room-meta"><span><i className="pi pi-map-marker" /> {room.building || 'Budynek nieokreślony'}</span><span><i className="pi pi-users" /> {room.capacity} miejsc</span></p>
            <div className="room-attrs">{room.attributes.length ? room.attributes.map(attr => <span className={`small-chip ${filters.attributes.includes(attr.id) ? 'match' : ''}`} key={attr.id}>{attr.name}</span>) : <span className="empty-attr">Brak wyposażenia</span>}</div>
          </div>
          <Link className="p-button p-button-rounded calendar-btn" to={`/calendar/${room.id}`}><i className="pi pi-calendar" aria-hidden="true" /> Kalendarz</Link>
        </article>)}
      </div>
      {rooms.data?.length === 0 && <div className="surface empty"><i className="pi pi-search" /><h3>Brak sal spełniających kryteria</h3><p className="muted">Zmień kryteria lub zresetuj filtry.</p><Button label="Resetuj filtry" icon="pi pi-refresh" outlined onClick={reset} /></div>}
    </section>
  </main>;
}
