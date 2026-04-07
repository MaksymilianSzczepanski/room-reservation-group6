(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const calendarEl = document.getElementById("calendar");
    const roomSelect = document.getElementById("room-select");

    const roomNameEl = document.getElementById("room-name");
    const roomBuildingEl = document.getElementById("room-building");
    const roomCapacityEl = document.getElementById("room-capacity");
    const roomAttrsEl = document.getElementById("room-attrs");
    const roomDescriptionEl = document.getElementById("room-description");

    const reserveBtn = document.getElementById("reserve-btn");
    const reserveHintEl = document.getElementById("reserve-hint");
    const toastEl = document.getElementById("reservation-toast");

    const modalEl = document.getElementById("reservation-modal");
    const reservationForm = document.getElementById("reservation-form");
    const reservationErrorEl = document.getElementById("reservation-error");
    const reservationTitleEl = document.getElementById("reservation-form-title");
    const reservationStartEl = document.getElementById("reservation-start");
    const reservationEndEl = document.getElementById("reservation-end");
    const reservationNoteEl = document.getElementById("reservation-note");

    let toastTimer = null;
    let lastSelectedRange = null;

    const initialRoom = new URLSearchParams(window.location.search).get("room") || "";
    if (roomSelect && initialRoom) {
      roomSelect.value = initialRoom;
    }

    function getSelectedRoom() {
      return roomSelect ? roomSelect.value : initialRoom;
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: "dayGridMonth",
      height: "auto",
      locale: "pl",
      selectable: true,
      selectMirror: true,
      displayEventEnd: true,
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "dayGridMonth,timeGridWeek,timeGridDay",
      },
      buttonText: {
        today: "Dzis",
        month: "Miesiac",
        week: "Tydzien",
        day: "Dzien",
      },
      eventTimeFormat: {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      },
      slotLabelFormat: { hour: "2-digit", minute: "2-digit" },
      events: fetchEvents,
      eventContent(arg) {
        const wrapper = document.createElement("div");
        wrapper.className = "calendar-event";

        const timeLine = document.createElement("div");
        timeLine.className = "calendar-event-time";
        timeLine.textContent = buildEventTimeRange(arg.event.start, arg.event.end);

        const titleLine = document.createElement("div");
        titleLine.className = "calendar-event-title";
        titleLine.textContent = arg.event.title || "Rezerwacja";

        wrapper.appendChild(timeLine);
        wrapper.appendChild(titleLine);

        return { domNodes: [wrapper] };
      },
      select(info) {
        const roomId = getSelectedRoom();
        if (!roomId) {
          showToast("Najpierw wybierz konkretna sale.");
          calendar.unselect();
          return;
        }

        lastSelectedRange = {
          start: info.start,
          end: info.end,
        };
        openReservationModal(lastSelectedRange.start, lastSelectedRange.end);
      },
      eventClick(info) {
        const props = info.event.extendedProps;
        alert(`Tytul: ${props.title || info.event.title || "-"}\nSala: ${props.room}\nStatus: ${props.status}\nNotatka: ${props.note || "-"}\nRezerwujacy: ${props.user}`);
      },
    });

    calendar.render();

    if (roomSelect) {
      roomSelect.addEventListener("change", () => {
        syncRoomParam(roomSelect.value);
        updateRoomSummary(roomSelect.value);
        lastSelectedRange = null;
        calendar.refetchEvents();
      });

      syncRoomParam(roomSelect.value);
    }

    if (reserveBtn) {
      reserveBtn.addEventListener("click", () => {
        const roomId = getSelectedRoom();
        if (!roomId) {
          showToast("Wybierz sale, aby zlozyc rezerwacje.");
          return;
        }

        const range = lastSelectedRange || getDefaultReservationRange();
        openReservationModal(range.start, range.end);
      });
    }

    if (modalEl) {
      modalEl.querySelectorAll("[data-close-reservation]").forEach((el) => {
        el.addEventListener("click", closeReservationModal);
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeReservationModal();
        }
      });
    }

    if (reservationForm) {
      reservationForm.addEventListener("submit", submitReservation);
    }

    updateRoomSummary(getSelectedRoom());

    function syncRoomParam(roomId) {
      const url = new URL(window.location.href);
      if (roomId) {
        url.searchParams.set("room", roomId);
      } else {
        url.searchParams.delete("room");
      }
      window.history.replaceState({}, "", url);
    }

    async function updateRoomSummary(roomId) {
      if (!roomId) {
        roomNameEl.textContent = "Wszystkie sale";
        roomBuildingEl.textContent = "Brak filtra";
        roomCapacityEl.textContent = "Wybierz konkretna sale, aby zobaczyc szczegoly.";
        roomAttrsEl.innerHTML = "";
        roomDescriptionEl.textContent = "";
        if (reserveBtn) reserveBtn.disabled = true;
        if (reserveHintEl) reserveHintEl.textContent = "Wybierz sale, aby zlozyc prosbe o rezerwacje.";
        return;
      }

      try {
        const response = await fetch(`/api/rooms/${roomId}/`);
        if (!response.ok) {
          throw new Error("Nie mozna pobrac danych sali");
        }

        const room = await response.json();
        roomNameEl.textContent = room.name || "Sala";
        roomBuildingEl.textContent = room.building || "Bez budynku";
        roomCapacityEl.textContent = `Pojemnosc: ${room.capacity} miejsc`;

        if (room.attributes && room.attributes.length) {
          roomAttrsEl.innerHTML = room.attributes
            .map((attr) => `<span class="attr-chip">${attr.name}</span>`)
            .join("");
        } else {
          roomAttrsEl.innerHTML = '<span class="attr-chip">Brak atrybutow</span>';
        }

        roomDescriptionEl.textContent = room.description || "";
        if (reserveBtn) reserveBtn.disabled = false;
        if (reserveHintEl) reserveHintEl.textContent = "Mozesz kliknac Zarezerwuj albo zaznaczyc zakres na kalendarzu.";
      } catch (error) {
        roomNameEl.textContent = "Nie udalo sie pobrac danych sali";
        roomBuildingEl.textContent = "Blad";
        roomCapacityEl.textContent = "";
        roomAttrsEl.innerHTML = "";
        roomDescriptionEl.textContent = "Sprobuj ponownie za chwile.";
        if (reserveBtn) reserveBtn.disabled = true;
        if (reserveHintEl) reserveHintEl.textContent = "Brak danych sali - rezerwacja chwilowo niedostepna.";
      }
    }

    function fetchEvents(fetchInfo, successCallback, failureCallback) {
      const room = getSelectedRoom();
      const params = new URLSearchParams();
      if (room) params.append("room", room);

      fetch(`/api/events/?${params.toString()}`)
        .then((r) => {
          if (!r.ok) throw new Error("Blad pobierania eventow");
          return r.json();
        })
        .then((data) => successCallback(data))
        .catch((err) => failureCallback(err));
    }

    function openReservationModal(startDate, endDate) {
      if (!modalEl) return;

      reservationStartEl.value = formatDateTimeLocal(startDate);
      reservationEndEl.value = formatDateTimeLocal(endDate);
      hideReservationError();
      modalEl.classList.add("is-open");
      modalEl.setAttribute("aria-hidden", "false");
      document.body.classList.add("reservation-open");
      if (reservationTitleEl) reservationTitleEl.focus();
    }

    function closeReservationModal() {
      if (!modalEl) return;
      modalEl.classList.remove("is-open");
      modalEl.setAttribute("aria-hidden", "true");
      document.body.classList.remove("reservation-open");
      hideReservationError();
      calendar.unselect();
    }

    async function submitReservation(event) {
      event.preventDefault();

      const roomId = getSelectedRoom();
      if (!roomId) {
        showReservationError("Nie wybrano sali do rezerwacji.");
        return;
      }

      const startValue = reservationStartEl.value;
      const endValue = reservationEndEl.value;
      if (!startValue || !endValue) {
        showReservationError("Uzupelnij poczatek i koniec rezerwacji.");
        return;
      }

      const startDate = new Date(startValue);
      const endDate = new Date(endValue);
      if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        showReservationError("Nieprawidlowy format daty.");
        return;
      }

      if (endDate <= startDate) {
        showReservationError("Koniec rezerwacji musi byc pozniejszy niz poczatek.");
        return;
      }

      const submitBtn = reservationForm.querySelector(".submit-btn");
      submitBtn.disabled = true;
      submitBtn.textContent = "Wysylam...";
      hideReservationError();

      try {
        const response = await fetch("/api/reservations/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            room: Number(roomId),
            title: ((reservationTitleEl && reservationTitleEl.value) || "").trim(),
            start: startDate.toISOString(),
            end: endDate.toISOString(),
            note: (reservationNoteEl.value || "").trim(),
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(extractErrorMessage(errorData));
        }

        reservationForm.reset();
        closeReservationModal();
        calendar.refetchEvents();
        showToast("Prosba o rezerwacje zostala wyslana.");
      } catch (error) {
        showReservationError(error.message || "Nie udalo sie wyslac prosby o rezerwacje.");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Wyslij prosbe";
      }
    }

    function getDefaultReservationRange() {
      const start = new Date();
      start.setMinutes(0, 0, 0);
      start.setHours(start.getHours() + 1);
      const end = new Date(start.getTime() + 60 * 60 * 1000);
      return { start, end };
    }

    function formatDateTimeLocal(value) {
      const date = new Date(value);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      const hours = String(date.getHours()).padStart(2, "0");
      const minutes = String(date.getMinutes()).padStart(2, "0");
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    function buildEventTimeRange(start, end) {
      if (!start) return "";
      const startText = formatTime(start);
      if (!end) return startText;
      return `${startText} - ${formatTime(end)}`;
    }

    function formatTime(date) {
      return new Intl.DateTimeFormat("pl-PL", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(date);
    }

    function showToast(message) {
      if (!toastEl) return;
      toastEl.textContent = message;
      toastEl.classList.add("show");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        toastEl.classList.remove("show");
      }, 2600);
    }

    function showReservationError(message) {
      if (!reservationErrorEl) return;
      reservationErrorEl.hidden = false;
      reservationErrorEl.textContent = message;
    }

    function hideReservationError() {
      if (!reservationErrorEl) return;
      reservationErrorEl.hidden = true;
      reservationErrorEl.textContent = "";
    }

    function getCsrfToken() {
      const tokenCookie = document.cookie
        .split(";")
        .map((item) => item.trim())
        .find((item) => item.startsWith("csrftoken="));
      return tokenCookie ? decodeURIComponent(tokenCookie.split("=")[1]) : "";
    }

    function extractErrorMessage(errorData) {
      if (!errorData) return "Nie udalo sie wyslac prosby o rezerwacje.";

      if (typeof errorData === "string") return errorData;
      if (Array.isArray(errorData) && errorData.length) return String(errorData[0]);
      if (errorData.detail) return String(errorData.detail);
      if (errorData.non_field_errors && errorData.non_field_errors.length) {
        return String(errorData.non_field_errors[0]);
      }

      for (const key of Object.keys(errorData)) {
        const value = errorData[key];
        if (Array.isArray(value) && value.length) return String(value[0]);
        if (typeof value === "string" && value.trim()) return value;
      }

      return "Nie udalo sie wyslac prosby o rezerwacje.";
    }
  });
})();

