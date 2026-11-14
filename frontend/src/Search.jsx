import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { api } from './api';
import { Feedback, useData } from './ui';

const empty = { building: '', name: '', minimum: '', maximum: '', attributes: [] };
export default function Search() {
  const [filters, setFilters] = useState(empty);
  const [query, setQuery] = useState('');
  const rooms = useData(() => api(`search/${query ? `?${query}` : ''}`), [query]);
  const attributes = useData(() => api('rooms/attributes/'));
  const buildings = useData(() => api('rooms/'));
  function submit(e) {
    e.preventDefault(); const params = new URLSearchParams();
    for (const [key, value] of Object.entries({ building__icontains: filters.building, name__icontains: filters.name, capacity__gte: filters.minimum, capacity__lte: filters.maximum })) if (value) params.set(key, value);
    filters.attributes.forEach(id => params.append('attributes__id', id));
    const next = params.toString(); if (query === next) rooms.reload(); else setQuery(next);
  }
  const field = (key, value) => setFilters({ ...filters, [key]: value });
  return <main className="search-page">
    <div className="logo-container"><img src="/images/logo.png" alt="UniwRersu" /></div>
    <h1 className="subtitle">Wyszukaj sale</h1>
    <form className="search-container" onSubmit={submit}>
      <label className="search-field"><i className="pi pi-building" /><span>Budynek</span><InputText list="buildings" placeholder="Wszystkie budynki" value={filters.building} onChange={e => field('building', e.target.value)} /></label>
      <datalist id="buildings">{[...new Set((buildings.data || []).map(room => room.building))].map(value => <option key={value} value={value} />)}</datalist>
      <label className="search-field"><i className="pi pi-search" /><span>Nazwa sali</span><InputText placeholder="Np. sala wykładowa" value={filters.name} onChange={e => field('name', e.target.value)} /></label>
      <div className="search-field"><i className="pi pi-users" /><span>Liczba miejsc</span><div className="capacity-inputs"><InputText aria-label="Minimalna liczba miejsc" type="number" min="1" placeholder="Od" value={filters.minimum} onChange={e => field('minimum', e.target.value)} /><span>–</span><InputText aria-label="Maksymalna liczba miejsc" type="number" min={filters.minimum || 1} placeholder="Do" value={filters.maximum} onChange={e => field('maximum', e.target.value)} /></div></div>
      <div className="search-actions"><Button type="submit" label="Szukaj" icon="pi pi-search" rounded /><Button type="button" aria-label="Wyczyść filtry" icon="pi pi-filter-slash" rounded outlined onClick={() => { setFilters(empty); setQuery(''); }} /></div>
    </form>
    <div className="attributes"><span className="attr-title">Wyposażenie sali</span><div className="chips">{attributes.data?.map(attr => <button type="button" className={`chip ${filters.attributes.includes(attr.id) ? 'active' : ''}`} aria-pressed={filters.attributes.includes(attr.id)} key={attr.id} onClick={() => field('attributes', filters.attributes.includes(attr.id) ? filters.attributes.filter(id => id !== attr.id) : [...filters.attributes, attr.id])}>{attr.name}</button>)}{attributes.data?.length === 0 && <span>Brak zdefiniowanego wyposażenia</span>}</div></div>
    <Feedback error={attributes.error || buildings.error} />
    <section className="results" aria-label="Wyniki wyszukiwania"><div className="results-header"><h2>Dostępne sale</h2>{rooms.data && <span className="results-count">Liczba sal: {rooms.data.length}</span>}</div>
      <Feedback {...rooms} />
      {rooms.data?.map(room => <article className="room-card" key={room.id}><div><h3>{room.name}</h3><p className="room-meta"><i className="pi pi-building" /> {room.building || 'Budynek nieokreślony'} <span>·</span> <i className="pi pi-users" /> {room.capacity} miejsc</p><div className="room-attrs">{room.attributes.map(attr => <span className="small-chip" key={attr.id}>{attr.name}</span>)}</div></div><Link className="p-button" to={`/calendar/${room.id}`}><i className="pi pi-calendar" /> Kalendarz</Link></article>)}
      {rooms.data?.length === 0 && <div className="surface empty"><i className="pi pi-search" /><h3>Brak sal spełniających kryteria</h3><p>Zmień lub wyczyść filtry wyszukiwania.</p></div>}
    </section>
  </main>;
}
