from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AusenciaForm, TecnicoOperativoForm, TurnoForm
from .models import Ausencia, TecnicoOperativo, Turno


class PermissionedMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = False


class TecnicoOperativoListView(PermissionedMixin, ListView):
    model = TecnicoOperativo
    template_name = "personal/tecnico_list.html"
    context_object_name = "tecnicos"
    permission_required = "personal.view_tecnicooperativo"


class TecnicoOperativoCreateView(PermissionedMixin, CreateView):
    model = TecnicoOperativo
    form_class = TecnicoOperativoForm
    template_name = "personal/tecnico_form.html"
    success_url = reverse_lazy("personal:tecnico_list")
    permission_required = "personal.add_tecnicooperativo"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TecnicoOperativoUpdateView(PermissionedMixin, UpdateView):
    model = TecnicoOperativo
    form_class = TecnicoOperativoForm
    template_name = "personal/tecnico_form.html"
    success_url = reverse_lazy("personal:tecnico_list")
    permission_required = "personal.change_tecnicooperativo"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TecnicoOperativoDeleteView(PermissionedMixin, DeleteView):
    model = TecnicoOperativo
    template_name = "personal/confirm_delete.html"
    success_url = reverse_lazy("personal:tecnico_list")
    permission_required = "personal.delete_tecnicooperativo"


class TurnoListView(PermissionedMixin, ListView):
    model = Turno
    template_name = "personal/turno_list.html"
    context_object_name = "turnos"
    permission_required = "personal.view_turno"


class TurnoCreateView(PermissionedMixin, CreateView):
    model = Turno
    form_class = TurnoForm
    template_name = "personal/turno_form.html"
    success_url = reverse_lazy("personal:turno_list")
    permission_required = "personal.add_turno"

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)


class TurnoUpdateView(PermissionedMixin, UpdateView):
    model = Turno
    form_class = TurnoForm
    template_name = "personal/turno_form.html"
    success_url = reverse_lazy("personal:turno_list")
    permission_required = "personal.change_turno"


class TurnoDeleteView(PermissionedMixin, DeleteView):
    model = Turno
    template_name = "personal/confirm_delete.html"
    success_url = reverse_lazy("personal:turno_list")
    permission_required = "personal.delete_turno"


class AusenciaListView(PermissionedMixin, ListView):
    model = Ausencia
    template_name = "personal/ausencia_list.html"
    context_object_name = "ausencias"
    permission_required = "personal.view_ausencia"

    def get_queryset(self):
        qs = super().get_queryset()
        fecha_inicio = self.request.GET.get("inicio")
        fecha_fin = self.request.GET.get("fin")
        if fecha_inicio:
            try:
                inicio_valor = datetime.fromisoformat(fecha_inicio)
                if hasattr(inicio_valor, 'date'):
                    inicio_valor = inicio_valor.date()
                qs = qs.filter(fecha_inicio__gte=inicio_valor)
            except ValueError:
                pass
        if fecha_fin:
            try:
                fin_valor = datetime.fromisoformat(fecha_fin)
                if hasattr(fin_valor, 'date'):
                    fin_valor = fin_valor.date()
                qs = qs.filter(fecha_fin__lte=fin_valor)
            except ValueError:
                pass
        return qs


class AusenciaCreateView(PermissionedMixin, CreateView):
    model = Ausencia
    form_class = AusenciaForm
    template_name = "personal/ausencia_form.html"
    success_url = reverse_lazy("personal:ausencia_list")
    permission_required = "personal.add_ausencia"


class AusenciaUpdateView(PermissionedMixin, UpdateView):
    model = Ausencia
    form_class = AusenciaForm
    template_name = "personal/ausencia_form.html"
    success_url = reverse_lazy("personal:ausencia_list")
    permission_required = "personal.change_ausencia"


class AusenciaDeleteView(PermissionedMixin, DeleteView):
    model = Ausencia
    template_name = "personal/confirm_delete.html"
    success_url = reverse_lazy("personal:ausencia_list")
    permission_required = "personal.delete_ausencia"


class AgendaResumenView(PermissionedMixin, View):
    """Devuelve información resumida en JSON para calendarios o tableros."""

    permission_required = "personal.view_turno"

    def get(self, request, *args, **kwargs):
        hoy = timezone.now()
        turnos = [
            {
                "id": turno.id,
                "title": turno.nombre,
                "start": turno.fecha_inicio.isoformat(),
                "end": turno.fecha_fin.isoformat(),
                "color": turno.color,
                "tecnicos": [t.nombre_display for t in turno.tecnicos.all()],
            }
            for turno in Turno.objects.filter(fecha_fin__gte=hoy - timedelta(days=7)).order_by('fecha_inicio')
        ]
        ausencias = [
            {
                "id": ausencia.id,
                "title": f"{ausencia.get_tipo_display()} - {ausencia.tecnico}",
                "start": ausencia.fecha_inicio.isoformat(),
                "end": ausencia.fecha_fin.isoformat(),
                "status": ausencia.estado,
                "tecnico": str(ausencia.tecnico),
            }
            for ausencia in Ausencia.objects.filter(fecha_fin__gte=(hoy.date() - timedelta(days=30))).order_by('fecha_inicio')
        ]
        return JsonResponse({"turnos": turnos, "ausencias": ausencias})