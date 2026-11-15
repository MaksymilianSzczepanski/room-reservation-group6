import { expect, test } from '@playwright/test';

const room = { id: 1, name: 'Sala 101', building: 'Budynek A', capacity: 30, description: 'Sala wykładowa', attributes: [] };
async function mockApi(page, actor = { id: 2, username: 'pracownik', is_admin: false, is_student: false }) {
  const posts = [];
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    let value = [];
    if (url.pathname === '/api/search/' || url.pathname === '/api/rooms/') value = [room];
    if (url.pathname === '/api/rooms/1/') value = room;
    if (url.pathname === '/api/users/login/') value = { token: 'test-token', user: actor };
    if (url.pathname === '/api/users/me/') value = actor;
    if (url.pathname === '/api/reservations/' && request.method() === 'POST') { posts.push(request.postDataJSON()); value = { id: 1, ...request.postDataJSON(), status: 'pending', notification_status: 'sent' }; }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) });
  });
  return posts;
}
test('gość przegląda wyszukiwarkę i kalendarz bez logowania', async ({ page }) => {
  await mockApi(page); const privateRequests = [];
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/reservations/') privateRequests.push(request.url()); });
  await page.goto('/'); await expect(page.getByRole('heading', { name: 'Sala 101' })).toBeVisible();
  await page.getByRole('link', { name: 'Kalendarz', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Kalendarz rezerwacji' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Kalendarz sali' })).toBeVisible();
  await expect(page.getByText('Kalendarz dostępny bez logowania', { exact: false })).toBeVisible();
  expect(privateRequests).toEqual([]);
});
test('pracownik loguje się i składa wniosek z datami w strefie Warszawy', async ({ page }) => {
  const posts = await mockApi(page); await page.goto('/calendar/1');
  await page.getByRole('button', { name: 'Zaloguj się, aby zarezerwować' }).click();
  const login = page.getByRole('dialog'); await login.getByLabel('Login').fill('pracownik'); await login.getByLabel('Hasło').fill('test-password'); await login.getByRole('button', { name: 'Zaloguj', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Wniosek o rezerwację' })).toBeVisible();
  const dialog = page.getByRole('dialog'); await dialog.getByLabel('Tytuł').fill('Spotkanie');
  await dialog.getByLabel('Początek').fill('2026-12-01T09:00'); await dialog.getByLabel('Koniec').fill('2026-12-01T10:00');
  await dialog.getByRole('button', { name: 'Wyślij wniosek' }).click();
  await expect(page.getByText('Wniosek o rezerwację został wysłany do opiekuna.')).toBeVisible();
  expect(posts).toHaveLength(1); expect(posts[0].start).toBe('2026-12-01T09:00:00.000+01:00'); expect(posts[0].room_id).toBe(1);
});
test('wyszukiwarka filtruje po kilku elementach wyposażenia i resetuje filtry', async ({ page }) => {
  const queries = [];
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()); let value = [];
    if (url.pathname === '/api/rooms/attributes/') value = [{ id: 1, name: 'Rzutnik' }, { id: 2, name: 'Komputer' }, { id: 3, name: 'Tablica' }];
    if (url.pathname === '/api/search/') { queries.push(url.searchParams.getAll('attributes__id')); value = [room]; }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Rzutnik' }).click();
  await page.getByRole('button', { name: 'Komputer' }).click();
  await expect(page.getByRole('button', { name: 'Rzutnik' })).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(() => queries.at(-1)).toEqual(['1', '2']);
  await page.getByRole('button', { name: 'Resetuj filtry' }).first().click();
  await expect(page.getByRole('button', { name: 'Rzutnik' })).toHaveAttribute('aria-pressed', 'false');
  await expect.poll(() => queries.at(-1)).toEqual([]);
});
test('zaznaczenie godzin w kalendarzu otwiera formularz z wypełnionym terminem', async ({ page }) => {
  const posts = await mockApi(page); await page.addInitScript(() => sessionStorage.setItem('room-reservation-token', 'test-token'));
  await page.goto('/calendar/1'); await page.getByRole('button', { name: /tydzień/i }).click();
  const column = page.locator('.fc-timegrid-col[data-date]').first(); const date = await column.getAttribute('data-date');
  const box = await column.boundingBox(); const x = box.x + box.width / 2;
  const from = await page.locator('td.fc-timegrid-slot-lane[data-time="10:00:00"]').boundingBox();
  const to = await page.locator('td.fc-timegrid-slot-lane[data-time="11:30:00"]').boundingBox();
  await page.mouse.move(x, from.y + from.height / 2); await page.mouse.down();
  await page.mouse.move(x, to.y + to.height / 2, { steps: 8 }); await page.mouse.up();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByLabel('Początek')).toHaveValue(`${date}T10:00`);
  await expect(dialog.getByLabel('Koniec')).toHaveValue(`${date}T12:00`);
  await dialog.getByLabel('Tytuł').fill('Konsultacje'); await dialog.getByRole('button', { name: 'Wyślij wniosek' }).click();
  await expect(page.getByText('Wniosek o rezerwację został wysłany do opiekuna.')).toBeVisible();
  expect(posts[0].start.startsWith(`${date}T10:00:00`)).toBe(true); expect(posts[0].end.startsWith(`${date}T12:00:00`)).toBe(true);
});
test('zwykły pracownik nie otwiera administracji', async ({ page }) => {
  await mockApi(page); await page.addInitScript(() => sessionStorage.setItem('room-reservation-token', 'test-token'));
  await page.goto('/admin'); await expect(page.getByText('Ta strona jest dostępna dla administratora.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Dodaj użytkownika' })).toHaveCount(0);
});

test('student po zalogowaniu nie otrzymuje formularza rezerwacji', async ({ page }) => {
  const posts = await mockApi(page, { id: 3, username: 'student', is_student: true, is_admin: false });
  await page.goto('/calendar/1');
  await page.getByRole('button', { name: 'Zaloguj się, aby zarezerwować' }).click();
  const login = page.getByRole('dialog', { name: 'Logowanie pracownika' });
  await login.getByLabel('Login').fill('student'); await login.getByLabel('Hasło').fill('test-password');
  await login.getByRole('button', { name: 'Zaloguj', exact: true }).click();
  await expect(page.getByText('Konto studenta umożliwia przeglądanie kalendarza.')).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0); expect(posts).toHaveLength(0);
});

test('anulowanie logowania nie wznawia starego wniosku przy kolejnym logowaniu', async ({ page }) => {
  await mockApi(page); await page.goto('/calendar/1');
  await page.getByRole('button', { name: 'Zaloguj się, aby zarezerwować' }).click();
  await page.keyboard.press('Escape');
  await page.getByRole('banner').getByRole('button', { name: 'Zaloguj', exact: true }).click();
  const login = page.getByRole('dialog'); await login.getByLabel('Login').fill('pracownik');
  await login.getByLabel('Hasło').fill('test-password'); await login.getByRole('button', { name: 'Zaloguj', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Wyloguj' })).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('opiekun generuje raport zajętości sal dla wybranego okresu', async ({ page }) => {
  const requests = []; const report = { start: '2026-12-01', end: '2026-12-31', workdays_only: true, day_count: 23, hours_per_day: 15,
    total: { room_count: 1, available_hours: 345, approved_hours: 69, pending_hours: 3, reservation_count: 12, occupancy: 20, pending_share: 0.9 },
    rooms: [{ room_id: 1, name: 'Sala 101', building: 'Budynek A', capacity: 30, available_hours: 345, approved_hours: 69, pending_hours: 3, reservation_count: 12, occupancy: 20, pending_share: 0.9 }],
    by_weekday: [{ weekday: 0, available_hours: 60, approved_hours: 18, occupancy: 30 }] };
  await page.addInitScript(() => sessionStorage.setItem('room-reservation-token', 'test-token'));
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()); let value = [];
    if (url.pathname === '/api/users/me/') value = { id: 2, username: 'opiekun', is_admin: false, is_student: false };
    if (url.pathname === '/api/guardians/mine/') value = [{ id: 1, user_id: 2, room_id: 1 }];
    if (url.pathname === '/api/rooms/') value = [room];
    if (url.pathname === '/api/reports/occupancy/') { requests.push(Object.fromEntries(url.searchParams)); value = report; }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) });
  });
  await page.goto('/guardian'); await page.getByRole('button', { name: 'Raport zajętości' }).click();
  await page.getByLabel('Od').fill('2026-12-01'); await page.getByLabel('Do').fill('2026-12-31');
  await page.getByText('Tylko dni robocze').click(); await page.getByRole('button', { name: 'Generuj raport' }).click();
  await expect.poll(() => requests.at(-1)).toEqual({ start: '2026-12-01', end: '2026-12-31', workdays: '1' });
  await expect(page.locator('.occ-tile.occ-main strong')).toHaveText('20%');
  await expect(page.getByRole('img', { name: /Sala 101: zajętość 20%/ })).toBeVisible();
  const download = page.waitForEvent('download'); await page.getByRole('button', { name: 'Pobierz CSV' }).click();
  expect((await download).suggestedFilename()).toBe('raport-zajetosci-2026-12-01_2026-12-31.csv');
});
