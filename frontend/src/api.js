const KEY = 'room-reservation-token';
export const token = () => sessionStorage.getItem(KEY);
export function saveToken(value) { if (value) sessionStorage.setItem(KEY, value); else sessionStorage.removeItem(KEY); }
const messages = {
  'Invalid credentials': 'Nieprawidłowy login lub hasło.',
  'Invalid or expired token': 'Sesja wygasła. Zaloguj się ponownie.',
  'Bearer token required': 'Zaloguj się, aby kontynuować.',
  'Room is already reserved': 'Ten termin jest już zajęty. Wybierz inny.',
  'Reservations must fit one day between 07:00 and 22:00': 'Rezerwacja musi obejmować jeden dzień w godzinach 07:00–22:00.',
  'Not a guardian of this room': 'Nie jesteś opiekunem tej sali.',
  'Reservation already decided': 'Ten wniosek został już rozpatrzony.',
  'Username already exists': 'Ta nazwa użytkownika jest już zajęta.',
  'Guardian already assigned': 'Ten opiekun jest już przypisany do sali.',
  'Room is used by reservations or guardians': 'Sala ma rezerwacje lub przypisanych opiekunów. Nie można jej usunąć.',
};
export async function api(path, { method = 'GET', body, signal } = {}) {
  let result;
  try { result = await fetch(`/api/${path}`, { method, signal,
    headers: { ...(token() ? { Authorization: `Bearer ${token()}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}) });
  } catch (error) { if (error.name === 'AbortError') throw error; throw new Error('Brak połączenia z serwerem. Spróbuj ponownie.'); }
  const data = await result.json().catch(() => ({}));
  if (!result.ok) {
    if (result.status === 401 && path !== 'users/login/') { saveToken(null); window.dispatchEvent(new Event('session-expired')); }
    throw new Error(messages[data.error] || (result.status >= 500 ? 'Usługa jest chwilowo niedostępna. Spróbuj ponownie.' : data.error) || 'Nie udało się wykonać operacji.');
  }
  return data;
}
