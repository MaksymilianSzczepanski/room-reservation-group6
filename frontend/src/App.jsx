import { createContext, lazy, Suspense, useContext, useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Message } from 'primereact/message';
import { api, saveToken, token } from './api';
import { Feedback, Field, useData } from './ui';
import Search from './Search';
const CalendarPage = lazy(() => import('./CalendarPage'));
const Bookings = lazy(() => import('./Bookings'));
const Admin = lazy(() => import('./Admin'));

const Auth = createContext(null);
export const useAuth = () => useContext(Auth);

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!token());
  const [login, setLogin] = useState(false);
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const location = useLocation();
  const assignments = useData(() => user ? api('guardians/mine/') : Promise.resolve([]), [user?.id]);
  useEffect(() => {
    let active = true;
    if (token()) api('users/me/').then(value => { if (active) setUser(value); })
      .catch(err => { if (active) setError(err.message); }).finally(() => { if (active) setReady(true); });
    const expired = () => { setUser(null); setError('Sesja wygasła. Zaloguj się ponownie.'); };
    window.addEventListener('session-expired', expired);
    return () => { active = false; window.removeEventListener('session-expired', expired); };
  }, []);
  useEffect(() => { window.scrollTo(0, 0); }, [location.pathname]);
  async function signIn(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { const result = await api('users/login/', { method: 'POST', body: credentials });
      saveToken(result.token); setUser(result.user); setLogin(false); setCredentials({ username: '', password: '' });
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  function signOut() { saveToken(null); setUser(null); }
  const auth = { user, ready, openLogin: () => { setError(''); setLogin(true); } };
  return <Auth.Provider value={auth}><div className="hero"><div className="content">
    <header className="topbar"><Link className="home-link" to="/"><i className="pi pi-building" /> Rezerwacje sal</Link>
      <nav aria-label="Menu główne"><Link to="/">Wyszukiwarka</Link>
        {user && <Link to="/my-reservations">Moje rezerwacje</Link>}
        {!!assignments.data?.length && <Link to="/guardian">Panel opiekuna</Link>}
        {user?.is_admin && <Link to="/admin">Administracja</Link>}
        {user ? <><span className="username"><i className="pi pi-user" /> {user.username}</span><Button label="Wyloguj" icon="pi pi-sign-out" outlined onClick={signOut} /></> : <Button label="Zaloguj się" icon="pi pi-sign-in" onClick={auth.openLogin} />}
      </nav>
    </header>
    {error && !login && <Message severity="warn" text={error} />}
    <Feedback error={assignments.error} />
    {!ready ? <Feedback loading /> : <Suspense fallback={<Feedback loading />}><Routes>
      <Route path="/" element={<Search />} />
      <Route path="/calendar/:roomId" element={<CalendarPage />} />
      <Route path="/my-reservations" element={<RequireUser><Bookings /></RequireUser>} />
      <Route path="/guardian" element={<RequireUser><Bookings guardian /></RequireUser>} />
      <Route path="/admin" element={<RequireUser admin><Admin onAssignmentsChanged={assignments.reload} /></RequireUser>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Suspense>}
    <footer>UniwRersu · System rezerwacji sal</footer>
  </div></div>
    <Dialog header="Zaloguj się" visible={login} modal onHide={() => { setLogin(false); setCredentials({ username: '', password: '' }); }} style={{ width: '26rem' }} breakpoints={{ '600px': '94vw' }}>
      <p className="muted">Konto pracownika umożliwia składanie wniosków o rezerwację. Przeglądanie sal i kalendarza jest dostępne bez logowania.</p>
      <form className="form-stack" onSubmit={signIn}>
        <Field label="Login"><InputText autoFocus autoComplete="username" required value={credentials.username} onChange={e => setCredentials({ ...credentials, username: e.target.value })} /></Field>
        <Field label="Hasło"><InputText type="password" autoComplete="current-password" required value={credentials.password} onChange={e => setCredentials({ ...credentials, password: e.target.value })} /></Field>
        <Feedback error={error} /><Button label="Zaloguj" type="submit" loading={busy} />
      </form>
    </Dialog>
  </Auth.Provider>;
}
function RequireUser({ children, admin = false }) {
  const { user, openLogin } = useAuth();
  if (!user) return <section className="surface empty"><h1>Zaloguj się, aby kontynuować</h1><Button label="Zaloguj się" onClick={openLogin} /></section>;
  if (admin && !user.is_admin) return <Message severity="warn" text="Ta strona jest dostępna dla administratora." />;
  return children;
}
