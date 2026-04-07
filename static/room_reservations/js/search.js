(async function () {
  const resultsEl = document.getElementById('results');
  const form = document.getElementById('search-form');
  const btnSearch = document.getElementById('btn-search');
  const buildingList = document.getElementById('building-list');
  const nameList = document.getElementById('name-list');
  const chipContainer = document.getElementById('attr-chips');
  const selectedAttrIds = new Set();
  const isAuthenticated = document.body.dataset.isAuthenticated === '1';
  const shouldOpenLoginModal = document.body.dataset.showLoginModal === '1';
  const openLoginBtn = document.getElementById('open-login-modal');
  const loginModal = document.getElementById('login-modal');
  let allRooms = [];

  btnSearch.addEventListener('click', (e) => { e.preventDefault(); runSearch(); });
  form.building.addEventListener('input', updateRoomHintsForBuilding);
  resultsEl.addEventListener('click', handleResultsClick);

  if (openLoginBtn) {
    openLoginBtn.addEventListener('click', openLoginModal);
  }

  if (loginModal) {
    loginModal.querySelectorAll('[data-close-login]').forEach((el) => {
      el.addEventListener('click', closeLoginModal);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeLoginModal();
    });

    if (shouldOpenLoginModal) {
      openLoginModal();
    }
  }

  await Promise.all([loadAttributes(), loadRoomHints()]);
  runSearch(true);

  async function loadAttributes() {
    const res = await fetch('/api/attributes/');
    if (!res.ok) return;
    const data = await res.json();
    const attributes = Array.isArray(data) ? data : (data.results || []);

    chipContainer.innerHTML = '';
    attributes.forEach(attr => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.textContent = attr.name;
      chip.dataset.id = attr.id;
      chip.addEventListener('click', () => {
        if (selectedAttrIds.has(attr.id)) {
          selectedAttrIds.delete(attr.id);
          chip.classList.remove('active');
        } else {
          selectedAttrIds.add(attr.id);
          chip.classList.add('active');
        }
        runSearch(false);
      });
      chipContainer.appendChild(chip);
    });
  }

  async function loadRoomHints() {
    const res = await fetch('/api/rooms/?page_size=1000');
    if (!res.ok) return;
    const rooms = await res.json();
    allRooms = Array.isArray(rooms) ? rooms : (rooms.results || []);

    const buildings = new Set();
    allRooms.forEach(room => {
      if (room.building) buildings.add(room.building);
    });

    renderDatalist(buildingList, Array.from(buildings).sort());
    updateRoomHintsForBuilding();
  }

  function normalize(value) {
    return (value || '').trim().toLowerCase();
  }

  function renderDatalist(listEl, values) {
    listEl.innerHTML = '';
    values.forEach(value => {
      const option = document.createElement('option');
      option.value = value;
      listEl.appendChild(option);
    });
  }

  function updateRoomHintsForBuilding() {
    const building = normalize(form.building.value);
    const selectedRoom = normalize(form.name.value);
    const filteredNames = new Set();

    allRooms.forEach(room => {
      const roomBuilding = normalize(room.building);
      const matchesBuilding = !building || roomBuilding.includes(building);
      if (matchesBuilding && room.name) filteredNames.add(room.name);
    });

    const roomOptions = Array.from(filteredNames).sort();
    renderDatalist(nameList, roomOptions);

    if (selectedRoom && !roomOptions.some(name => normalize(name) === selectedRoom)) {
      form.name.value = '';
    }
  }

  function buildQuery() {
    const params = new URLSearchParams();
    const building = form.building.value.trim();
    const name = form.name.value.trim();
    const minCap = form.min_capacity.value;
    const maxCap = form.max_capacity.value;

    if (building) params.append('building__icontains', building);
    if (name) params.append('name__icontains', name);
    if (minCap) params.append('capacity__gte', minCap);
    if (maxCap) params.append('capacity__lte', maxCap);

    selectedAttrIds.forEach(id => params.append('attributes__id', id));
    return params.toString();
  }

  async function runSearch(skipIfEmpty = false) {
    const query = buildQuery();
    if (skipIfEmpty && !query && selectedAttrIds.size === 0) {
      resultsEl.innerHTML = '<div class="empty">Wpisz kryteria lub wybierz atrybuty i wyszukaj sale.</div>';
      return;
    }

    resultsEl.innerHTML = '<div class="muted">Szukam...</div>';
    const res = await fetch('/api/rooms/?' + query);
    if (!res.ok) {
      resultsEl.innerHTML = '<div class="empty">Blad podczas wyszukiwania.</div>';
      return;
    }

    const data = await res.json();
    const rooms = Array.isArray(data) ? data : (data.results || []);
    renderResults(rooms);
  }

  function renderResults(rooms) {
    if (!rooms.length) {
      resultsEl.innerHTML = '<div class="empty">Brak sal spelniajacych kryteria.</div>';
      return;
    }

    const countLabel = rooms.length === 1 ? '1 sala' : `${rooms.length} sale`;
    const cards = rooms.map((room, index) => {
      const attrs = room.attributes?.length
        ? room.attributes.map(a => `<span class="small-chip">${a.name}</span>`).join('')
        : '<span class="empty-attr">Brak atrybutow</span>';
      const action = isAuthenticated
        ? `<a class="card-btn" href="/calendar/?room=${room.id}">Zobacz kalendarz</a>`
        : '<button type="button" class="card-btn login-required-btn">Zaloguj aby rezerwowac</button>';

      return `
        <article class="room-card" style="animation-delay:${index * 50}ms">
          <div class="room-main">
            <div class="room-name">${room.name}</div>
            <div class="room-meta">${room.building || 'Bez budynku'} · ${room.capacity} miejsc</div>
            <div class="room-attrs">${attrs}</div>
          </div>
          ${action}
        </article>
      `;
    }).join('');

    resultsEl.innerHTML = `
      <div class="results-header">
        <h3>Wyniki wyszukiwania</h3>
        <span class="results-count">${countLabel}</span>
      </div>
      <div class="results-grid">${cards}</div>
    `;
  }

  function handleResultsClick(event) {
    const loginTrigger = event.target.closest('.login-required-btn');
    if (!loginTrigger) return;
    event.preventDefault();
    openLoginModal();
  }

  function openLoginModal() {
    if (!loginModal) return;
    loginModal.classList.add('is-open');
    loginModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');

    const input = document.getElementById('modal-username');
    if (input) input.focus();
  }

  function closeLoginModal() {
    if (!loginModal) return;
    loginModal.classList.remove('is-open');
    loginModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
  }
})();
