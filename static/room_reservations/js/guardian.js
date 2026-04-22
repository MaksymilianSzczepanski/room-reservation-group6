(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const sidebarLinks = Array.from(document.querySelectorAll(".sidebar-link"));
    const sections = Array.from(document.querySelectorAll(".dashboard-section"));

    const decisionModal = document.getElementById("decision-modal");
    const decisionCards = Array.from(document.querySelectorAll(".pending-card"));
    const decisionTitleEl = document.getElementById("decision-title-value");
    const decisionRoomEl = document.getElementById("decision-room");
    const decisionUserEl = document.getElementById("decision-user");
    const decisionStartEl = document.getElementById("decision-start");
    const decisionEndEl = document.getElementById("decision-end");
    const decisionNoteEl = document.getElementById("decision-note");
    const decisionNoteWrapEl = document.getElementById("decision-note-wrap");
    const approveForm = document.getElementById("approve-form");
    const rejectForm = document.getElementById("reject-form");
    const decisionCommentEl = document.getElementById("decision-comment");

    sidebarLinks.forEach((link) => {
      link.addEventListener("click", () => {
        const targetId = link.dataset.target;
        if (!targetId) return;

        sidebarLinks.forEach((item) => item.classList.remove("active"));
        link.classList.add("active");

        sections.forEach((section) => {
          section.classList.toggle("active", section.id === targetId);
        });
      });
    });

    if (decisionModal) {
      decisionCards.forEach((card) => {
        card.addEventListener("click", () => {
          openDecisionModal(card);
        });
      });

      decisionModal.querySelectorAll("[data-close-decision]").forEach((closeEl) => {
        closeEl.addEventListener("click", closeDecisionModal);
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeDecisionModal();
        }
      });
    }

    function openDecisionModal(card) {
      const decisionUrl = card.dataset.decisionUrl || "";
      if (!decisionUrl) return;

      decisionTitleEl.textContent = (card.dataset.title || "").trim() || "(Bez tytulu)";
      decisionRoomEl.textContent = card.dataset.room || "-";
      decisionUserEl.textContent = card.dataset.user || "-";
      decisionStartEl.textContent = card.dataset.start || "-";
      decisionEndEl.textContent = card.dataset.end || "-";

      const note = (card.dataset.note || "").trim();
      if (note) {
        decisionNoteWrapEl.hidden = false;
        decisionNoteEl.textContent = note;
      } else {
        decisionNoteWrapEl.hidden = true;
        decisionNoteEl.textContent = "";
      }

      approveForm.action = decisionUrl;
      rejectForm.action = decisionUrl;
      if (decisionCommentEl) decisionCommentEl.value = "";

      decisionModal.classList.add("is-open");
      decisionModal.setAttribute("aria-hidden", "false");
      document.body.classList.add("decision-open");
    }

    function closeDecisionModal() {
      if (!decisionModal) return;
      decisionModal.classList.remove("is-open");
      decisionModal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("decision-open");
      if (decisionCommentEl) decisionCommentEl.value = "";
    }
  });
})();
