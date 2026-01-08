from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from novedades.models import Novedad

from .forms import WorkOrderEstadoForm, WorkOrderForm
from .models import WorkOrder, WorkOrderEvento


class WorkOrderBoardView(LoginRequiredMixin, TemplateView):
    template_name = "ot/orden_tablero.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estado_filtro = self.request.GET.get("estado")
        busqueda = self.request.GET.get("q")
        queryset = WorkOrder.objects.select_related(
             "equipo", "responsable__user", "novedad_origen", "actividad"
        )

        if estado_filtro:
            queryset = queryset.filter(estado=estado_filtro)
        if busqueda:
            consecutivo_busqueda = None
            try:
                consecutivo_busqueda = int(busqueda)
            except (TypeError, ValueError):
                consecutivo_busqueda = None
            queryset = queryset.filter(
                Q(titulo__icontains=busqueda)
                | Q(descripcion__icontains=busqueda)
                | Q(equipo__nombre__icontains=busqueda)
                | Q(equipo__codigo__icontains=busqueda)
                | Q(equipo__tag__icontains=busqueda)
                | Q(equipo__numero_serie__icontains=busqueda)
                | (
                    Q(consecutivo=consecutivo_busqueda)
                    if consecutivo_busqueda is not None
                    else Q()
                )
            )
        agrupadas = {estado: [] for estado, _ in WorkOrder.ESTADOS}
        for orden in queryset.order_by("-fecha_creacion"):
            agrupadas[orden.estado].append(orden)

        conteos = {
            estado["estado"]: estado["total"]
            for estado in WorkOrder.objects.values("estado")
            .annotate(total=Count("id"))
            .order_by()
        }

        estados_definidos = [
            {
                "id": "pendiente",
                "titulo": "Pendiente",
                "descripcion": "Por revisar o planear",
                "color": "#f97316",
                "icono": "⏳",
            },
            {
                "id": "por_iniciar",
                "titulo": "Por iniciar",
                "descripcion": "Listo para asignar o ejecutar",
                "color": "#0891b2",
                "icono": "🧭",
            },
            {
                "id": "en_ejecucion",
                "titulo": "En ejecución",
                "descripcion": "Tareas activas en planta",
                "color": "#16a34a",
                "icono": "⚡",
            },
            {
                "id": "en_espera",
                "titulo": "En espera",
                "descripcion": "Bloqueadas por recursos/rep",
                "color": "#eab308",
                "icono": "⏸️",
            },
            {
                "id": "finalizada",
                "titulo": "Finalizada",
                "descripcion": "Listas para cierre y verificación",
                "color": "#0ea5e9",
                "icono": "✅",
            },
            {
                "id": "cancelada",
                "titulo": "Cancelada",
                "descripcion": "No continúa",
                "color": "#9ca3af",
                "icono": "🛑",
            },
        ]
        for estado in estados_definidos:
            estado["ordenes"] = agrupadas.get(estado["id"], [])
            estado["total"] = len(estado["ordenes"])
            estado["conteo_global"] = conteos.get(estado["id"], 0)

        context.update(
            {
                "busqueda": busqueda or "",
                "estado_filtro": estado_filtro or "",
                "estados_tablero": estados_definidos,
                
            }
        )
        return context


class WorkOrderCreateView(LoginRequiredMixin, CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "ot/orden_form.html"

    def get_initial(self):
        initial = super().get_initial()
        novedad_id = self.kwargs.get("novedad_id") or self.request.GET.get("novedad")
        if novedad_id:
            try:
                novedad = Novedad.objects.select_related("equipo").get(pk=novedad_id)
                actividad = (
                    novedad.actividad.nombre
                    if novedad.actividad
                    else "Novedad sin actividad"
                )
                initial.setdefault("novedad_origen", novedad.pk)
                initial.setdefault("titulo", f"Atender novedad: {actividad}")
                initial.setdefault("descripcion", novedad.descripcion)
                initial.setdefault("equipo", novedad.equipo_id)
                if novedad.actividad_id:
                    initial.setdefault("actividad", novedad.actividad_id)
            except Novedad.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        WorkOrderEvento.objects.create(
            orden=self.object,
            estado=self.object.estado,
            descripcion="Orden creada",
            creado_por=self.request.user,
        )
        if self.object.novedad_origen and self.object.novedad_origen.estado == "pendiente":
            self.object.novedad_origen.estado = "atendida"
            self.object.novedad_origen.save(update_fields=["estado"])
        messages.success(self.request, f"OT {self.object.codigo} creada exitosamente.")
        return response

    def get_success_url(self):
        return reverse("ot:orden_detalle", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        novedad_id = self.kwargs.get("novedad_id") or self.request.GET.get("novedad")
        if novedad_id:
            context["novedad_preseleccionada"] = Novedad.objects.filter(
                pk=novedad_id
            ).first()
        return context


class WorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "ot/orden_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f"Datos de la OT {self.object.codigo} actualizados."
        )
        return response

    def get_success_url(self):
        return reverse("ot:orden_detalle", args=[self.object.pk])


class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    model = WorkOrder
    template_name = "ot/orden_detalle.html"
    context_object_name = "orden"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "estado_form": WorkOrderEstadoForm(
                    initial={"estado": self.object.estado}
                ),
                "eventos": self.object.eventos.select_related("creado_por")[
                    :20
                ],
            }
        )
        return context


def actualizar_estado(request, pk):
    orden = get_object_or_404(WorkOrder, pk=pk)
    if request.method != "POST":
        return redirect("ot:orden_detalle", pk=pk)

    form = WorkOrderEstadoForm(request.POST)
    if form.is_valid():
        nuevo_estado = form.cleaned_data["estado"]
        nota = form.cleaned_data["nota"]
        cambios = []

        if nuevo_estado != orden.estado:
            orden.estado = nuevo_estado
            cambios.append("Estado actualizado.")

        if cambios:
            orden.save(update_fields=["estado", "fecha_actualizacion"])

        if nota or cambios:
            WorkOrderEvento.objects.create(
                orden=orden,
                estado=orden.estado,
                descripcion=nota or "Estado actualizado.",
                creado_por=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, "Movimos la OT y registramos el comentario.")
        else:
            messages.info(request, "No registramos cambios porque el estado es el mismo.")

    else:
        messages.error(request, "No pudimos actualizar el estado. Revisa el formulario.")

    return redirect("ot:orden_detalle", pk=pk)