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
  await page.getByRole('button', { name: 'Zarezerwuj salę', exact: true }).click();
  const dialog = page.getByRole('dialog'); await dialog.getByLabel('Tytuł').fill('Spotkanie');
  await dialog.getByLabel('Początek').fill('2026-12-01T09:00'); await dialog.getByLabel('Koniec').fill('2026-12-01T10:00');
  await dialog.getByRole('button', { name: 'Wyślij wniosek' }).click();
  await expect(page.getByText('Wniosek o rezerwację został wysłany do opiekuna.')).toBeVisible();
  expect(posts).toHaveLength(1); expect(posts[0].start).toBe('2026-12-01T09:00:00.000+01:00'); expect(posts[0].room_id).toBe(1);
});
test('zwykły pracownik nie otwiera administracji', async ({ page }) => {
  await mockApi(page); await page.addInitScript(() => sessionStorage.setItem('room-reservation-token', 'test-token'));
  await page.goto('/admin'); await expect(page.getByText('Ta strona jest dostępna dla administratora.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Dodaj użytkownika' })).toHaveCount(0);
});
