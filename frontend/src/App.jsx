import { createContext, lazy, Suspense, useContext, useEffect, useRef, useState } from 'react';
import { Link, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';
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
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const afterLogin = useRef(null);
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
      saveToken(result.token); setUser(result.user); setLogin(false); setShowPassword(false); setCapsLock(false); setCredentials({ username: '', password: '' });
      const next = afterLogin.current; afterLogin.current = null; next?.(result.user);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  function signOut() { saveToken(null); setUser(null); afterLogin.current = null; }
  const auth = { user, ready, openLogin: onSuccess => { afterLogin.current = typeof onSuccess === 'function' ? onSuccess : null; setError(''); setLogin(true); } };
  return <Auth.Provider value={auth}><div className="hero"><div className="content">
    <header className="topbar"><Link className="home-link" to="/"><span className="brand-mark"><i className="pi pi-building" /></span> Rezerwacje sal</Link>
      <nav aria-label="Menu główne"><NavLink className="nav-link" to="/" end><i className="pi pi-search" /> Wyszukiwarka</NavLink>
        {user && <NavLink className="nav-link" to="/my-reservations"><i className="pi pi-calendar" /> Moje rezerwacje</NavLink>}
        {!!assignments.data?.length && <NavLink className="nav-link" to="/guardian"><i className="pi pi-inbox" /> Panel opiekuna</NavLink>}
        {user?.is_admin && <NavLink className="nav-link" to="/admin"><i className="pi pi-cog" /> Administracja</NavLink>}
        {user ? <span className="user-box"><span className="username"><i className="pi pi-user" /> {user.username} · {user.is_admin ? 'Administrator' : user.is_student ? 'Student' : 'Pracownik'}</span><Button label="Wyloguj" icon="pi pi-sign-out" outlined rounded onClick={signOut} /></span> : <Button label="Zaloguj" icon="pi pi-sign-in" rounded onClick={auth.openLogin} />}
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
    <footer><i className="pi pi-building" /> UniwRersu · System rezerwacji sal · {new Date().getFullYear()}</footer>
  </div></div>
    <Dialog header="Logowanie pracownika" className="login-dialog" visible={login} modal dismissableMask={!busy} onHide={() => { if (busy) return; setLogin(false); setShowPassword(false); setCapsLock(false); afterLogin.current = null; setCredentials({ username: '', password: '' }); }} style={{ width: '27rem' }} breakpoints={{ '600px': '94vw' }}>
      <div className="login-brand"><img src="/images/logo.png" alt="" /><p>Zaloguj się kontem nadanym przez administratora systemu.</p></div>
      <form className="form-stack login-form" onSubmit={signIn}>
        <Field label="Login"><span className="input-with-icon"><i className="pi pi-user" aria-hidden="true" /><InputText autoFocus autoComplete="username" placeholder="Nazwa użytkownika" required value={credentials.username} onChange={e => setCredentials({ ...credentials, username: e.target.value })} /></span></Field>
        <Field label="Hasło"><span className="input-with-icon"><i className="pi pi-lock" aria-hidden="true" /><InputText type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••" required value={credentials.password} onKeyUp={e => setCapsLock(e.getModifierState?.('CapsLock') || false)} onChange={e => setCredentials({ ...credentials, password: e.target.value })} />
          <button type="button" className="password-toggle" aria-label={showPassword ? 'Ukryj wpisane znaki' : 'Pokaż wpisane znaki'} aria-pressed={showPassword} onClick={event => { event.preventDefault(); setShowPassword(value => !value); }}><i className={`pi ${showPassword ? 'pi-eye-slash' : 'pi-eye'}`} aria-hidden="true" /></button></span></Field>
        {capsLock && <small className="caps-warning"><i className="pi pi-exclamation-triangle" aria-hidden="true" /> Włączony Caps Lock</small>}
        <Feedback error={error} /><Button label="Zaloguj" icon="pi pi-sign-in" type="submit" loading={busy} className="login-submit" />
      </form>
      <ul className="login-roles" aria-label="Kto może się zalogować">
        <li><i className="pi pi-briefcase" aria-hidden="true" /><span><strong>Pracownik</strong> — składa wnioski o rezerwację sal</span></li>
        <li><i className="pi pi-shield" aria-hidden="true" /><span><strong>Opiekun i administrator</strong> — rozpatrują wnioski i zarządzają systemem</span></li>
        <li><i className="pi pi-eye" aria-hidden="true" /><span><strong>Student</strong> — przegląda sale i kalendarz bez logowania</span></li>
      </ul>
      <p className="login-help"><i className="pi pi-question-circle" aria-hidden="true" /> Nie pamiętasz hasła? Skontaktuj się z administratorem.</p>
    </Dialog>
  </Auth.Provider>;
}
function RequireUser({ children, admin = false }) {
  const { user, openLogin } = useAuth();
  if (!user) return <section className="surface empty"><h1>Zaloguj się, aby kontynuować</h1><Button label="Zaloguj się" onClick={openLogin} /></section>;
  if (admin && !user.is_admin) return <Message severity="warn" text="Ta strona jest dostępna dla administratora." />;
  return children;
}
