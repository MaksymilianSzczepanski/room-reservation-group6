from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import STATUS_APPROVED, STATUS_CANCELLED, STATUS_PENDING, STATUS_REJECTED
from .emails import notify_guardians_about_new_reservation, notify_requester_about_decision
from .models import Attribute, Reservation, Room
from .permissions import StudentsReadOnlyReservationPermission, can_create_reservations
from .serializers import RoomSerializer, ReservationSerializer, AttributeSerializer


def get_safe_next_url(request, candidate, default):
    value = (candidate or "").strip()
    if value and url_has_allowed_host_and_scheme(
        url=value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return default


def get_guardian_pending_count(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return Reservation.objects.filter(
        room__guardians__user=user,
        status=STATUS_PENDING,
    ).count()


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = "room_reservations/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rooms"] = Room.objects.all().order_by("name")
        context["selected_room"] = self.request.GET.get("room")
        context["can_create_reservations"] = can_create_reservations(self.request.user)
        return context


class SearchView(TemplateView):
    template_name = "room_reservations/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_url = reverse("search")
        requested_next = self.request.GET.get("next", "")
        next_target = get_safe_next_url(self.request, requested_next, search_url)
        show_login_from_next = (
            not self.request.user.is_authenticated
            and bool(requested_next)
            and next_target != search_url
        )

        context["next_target"] = next_target
        context["show_login_modal"] = bool(self.request.session.pop("show_login_modal", False)) or show_login_from_next
        context["login_error"] = self.request.session.pop("login_error", "")
        context["is_guardian"] = self.request.user.is_authenticated and self.request.user.guarded_rooms.exists()
        context["guardian_pending_count"] = get_guardian_pending_count(self.request.user)
        return context


class ModalLoginView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        search_url = reverse("search")
        next_url = get_safe_next_url(request, request.POST.get("next", ""), search_url)

        user = authenticate(request, username=username, password=password)
        if user is None:
            request.session["show_login_modal"] = True
            request.session["login_error"] = "Nieprawidlowy login lub haslo."
            if next_url != search_url:
                return redirect(f"{search_url}?{urlencode({'next': next_url})}")
            return redirect(search_url)

        login(request, user)
        return redirect(next_url)


class GuardianDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "room_reservations/guardian_dashboard.html"

    def test_func(self):
        return self.request.user.guarded_rooms.exists()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect("search")
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rooms_qs = (
            Room.objects.filter(guardians__user=self.request.user)
            .prefetch_related("attributes")
            .order_by("name")
        )
        pending_qs = (
            Reservation.objects.select_related("room", "user")
            .filter(room__guardians__user=self.request.user, status=STATUS_PENDING)
            .order_by("start")
        )
        recent_qs = (
            Reservation.objects.select_related("room", "user")
            .filter(room__guardians__user=self.request.user)
            .exclude(status=STATUS_PENDING)
            .order_by("-updated_at")[:15]
        )

        context["assigned_rooms"] = rooms_qs
        context["pending_requests"] = pending_qs
        context["pending_count"] = pending_qs.count()
        context["rooms_count"] = rooms_qs.count()
        context["history_count"] = recent_qs.count()
        context["recent_requests"] = recent_qs
        return context


class GuardianReservationDecisionView(LoginRequiredMixin, View):
    def post(self, request, reservation_id, *args, **kwargs):
        reservation = get_object_or_404(
            Reservation.objects.select_related("room", "user"),
            id=reservation_id,
        )
        if not reservation.room.guardians.filter(user=request.user).exists():
            messages.error(request, "Nie masz uprawnien do tej rezerwacji.")
            return redirect("guardian_dashboard")

        decision = request.POST.get("decision", "").strip()
        if decision not in {STATUS_APPROVED, STATUS_REJECTED}:
            messages.error(request, "Nieprawidlowa decyzja.")
            return redirect("guardian_dashboard")

        if reservation.status != STATUS_PENDING:
            messages.warning(request, "Ta prosba zostala juz rozpatrzona.")
            return redirect("guardian_dashboard")

        decision_comment = request.POST.get("decision_comment", "").strip()
        if decision == STATUS_REJECTED and not decision_comment:
            messages.error(request, "Podaj powod odrzucenia rezerwacji.")
            return redirect("guardian_dashboard")

        reservation.status = decision
        reservation.decision_comment = decision_comment if decision == STATUS_REJECTED else ""
        reservation.save(update_fields=["status", "decision_comment", "updated_at"])
        email_sent = notify_requester_about_decision(reservation, request)

        if decision == STATUS_APPROVED:
            messages.success(request, "Rezerwacja zostala zaakceptowana.")
        else:
            messages.success(request, "Rezerwacja zostala odrzucona.")
        if reservation.user.email and not email_sent:
            messages.warning(request, "Decyzja zostala zapisana, ale nie udalo sie wyslac maila.")

        next_url = get_safe_next_url(request, request.POST.get("next", ""), reverse("guardian_dashboard"))
        return redirect(next_url)


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.prefetch_related("attributes").order_by("name")
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = {
        "building": ["exact", "icontains"],
        "name": ["icontains"],
        "capacity": ["gte", "lte"],
        "attributes__id": ["in", "exact"],
    }
    search_fields = ["name", "building", "attributes__name"]
    ordering_fields = ["name", "capacity"]


class AttributeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Attribute.objects.all().order_by("name")
    serializer_class = AttributeSerializer
    permission_classes = [permissions.AllowAny]


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("room", "user").order_by("start")
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated, StudentsReadOnlyReservationPermission]
    filterset_fields = ["room", "status"]
    search_fields = ["title", "room__name", "user__username", "note"]
    ordering_fields = ["start", "end", "status"]

    def perform_create(self, serializer):
        try:
            reservation = serializer.save(user=self.request.user)
        except DjangoValidationError as exc:
            message = "; ".join(exc.messages) if getattr(exc, "messages", None) else str(exc)
            raise DRFValidationError(message) from exc
        notify_guardians_about_new_reservation(reservation, self.request)


class CalendarEventsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        room_id = request.GET.get("room")
        qs = Reservation.objects.select_related("room")

        if room_id:
            qs = qs.filter(room_id=room_id)

        now = timezone.now()
        qs = qs.filter(end__gte=now - timezone.timedelta(days=7))

        status_colors = {
            STATUS_PENDING: "#f97316",
            STATUS_APPROVED: "#22c55e",
            STATUS_REJECTED: "#ef4444",
            STATUS_CANCELLED: "#9ca3af",
        }

        events = []
        for res in qs:
            event_title = (res.title or "").strip() or res.room.name
            events.append(
                {
                    "id": res.id,
                    "title": event_title,
                    "start": res.start.isoformat(),
                    "end": res.end.isoformat(),
                    "color": status_colors.get(res.status, "#2563eb"),
                    "extendedProps": {
                        "title": event_title,
                        "room": res.room.name,
                        "status": res.status,
                        "note": res.note,
                        "user": res.user.username,
                    },
                }
            )

        return Response(events)
