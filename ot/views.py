from io import BytesIO
import io 
import pandas as pd

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, TemplateView, UpdateView

import pandas as pd

from activos.models import NodoActivo
from novedades.models import ActividadNovedad, Novedad
from personal.models import TecnicoOperativo

from .forms import WorkOrderBulkUploadForm, WorkOrderEstadoForm, WorkOrderForm
from .models import WorkOrder, WorkOrderAdjunto, WorkOrderEvento, WorkOrderEventoFoto

from django.contrib.auth.decorators import login_required
@login_required
def descargar_plantilla_carga_masiva(request):
    columnas = [
        "titulo",
        "equipo_codigo",
        "equipo_tag",
        "descripcion",
        "responsable_nombre",
        "actividad",
        "estado",
        "prioridad",
        "fecha_programada",
        "fecha_cierre_compromiso",
    ]
    plantilla_df = pd.DataFrame(columns=columnas)
    ejemplo_df = pd.DataFrame(
        [
            {
                "titulo": "Cambio de aceite preventivo",
                "equipo_codigo": "EQ-001",
                "equipo_tag": "",
                "descripcion": "Mantenimiento preventivo del motor principal",
                "responsable_nombre": "Nombre del técnico",
                "actividad": "Inspección general",
                 "estado": "reportada",
                "prioridad": "media",
                "fecha_programada": "2025-01-15",
                "fecha_cierre_compromiso": "2025-01-20",
            }
        ]
    )
    guia_df = pd.DataFrame(
        [
            {
                "campo": "titulo",
                "obligatorio": "Sí",
                "descripcion": "Nombre corto de la orden",
                "ejemplo": "Cambio de aceite preventivo",
            },
            {
                "campo": "equipo_codigo / equipo_tag",
                "obligatorio": "Sí (uno de los dos)",
                "descripcion": "Código interno o tag del equipo",
                "ejemplo": "EQ-001 / TAG-01",
            },
            {
                "campo": "estado",
                "obligatorio": "No",
                 "descripcion": "reportada, por_iniciar, en_ejecucion, en_espera, finalizada, cancelada",
                "ejemplo": "reportada",
            },
            {
                "campo": "prioridad",
                "obligatorio": "No",
                "descripcion": "alta, media, baja",
                "ejemplo": "media",
            },
            {
                "campo": "fecha_programada / fecha_cierre_compromiso",
                "obligatorio": "No",
                "descripcion": "Formato YYYY-MM-DD",
                "ejemplo": "2025-01-15",
            },
        ]
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        plantilla_df.to_excel(writer, index=False, sheet_name="plantilla")
        ejemplo_df.to_excel(writer, index=False, sheet_name="ejemplo")
        guia_df.to_excel(writer, index=False, sheet_name="guia")

    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        'attachment; filename="plantilla_carga_ot.xlsx"'
    )
    return response



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
                "id": "reportada",
                "titulo": "Reportada",
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
        for archivo in form.cleaned_data.get("adjuntos", []):
            WorkOrderAdjunto.objects.create(
                orden=self.object,
                archivo=archivo,
                creado_por=self.request.user,
            )
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
        for archivo in form.cleaned_data.get("adjuntos", []):
            WorkOrderAdjunto.objects.create(
                orden=self.object,
                archivo=archivo,
                creado_por=self.request.user,
            )
        messages.success(
            self.request, f"Datos de la OT {self.object.codigo} actualizados."
        )
        return response

    def get_success_url(self):
        return reverse("ot:orden_detalle", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["adjuntos"] = self.object.adjuntos.select_related("creado_por")[:12]
        return context


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
                "eventos": self.object.eventos.select_related("creado_por")
                .prefetch_related("adjuntos")[:20],
                "adjuntos": self.object.adjuntos.select_related("creado_por")[:12],
            }
        )
        return context

class WorkOrderBulkUploadView(LoginRequiredMixin, FormView):
    template_name = "ot/orden_carga_masiva.html"
    form_class = WorkOrderBulkUploadForm

    def form_valid(self, form):
        archivo = form.cleaned_data["archivo_excel"]
        try:
            df = pd.read_excel(archivo)
        except Exception:
            messages.error(self.request, "No pudimos leer el archivo. Verifica el formato.")
            return self.form_invalid(form)

        df.columns = [
            str(col).strip().lower().replace(" ", "_").replace("-", "_")
            for col in df.columns
        ]

        df = df.dropna(how="all")
        if df.empty:
            messages.error(
                self.request,
                "El archivo no tiene filas con información. Completa la hoja plantilla e inténtalo de nuevo.",
            )
            return self.form_invalid(form)

        required_columns = {"titulo"}
        missing = required_columns - set(df.columns)
        if missing:
            messages.error(
                self.request,
                "Faltan columnas obligatorias: " + ", ".join(sorted(missing)),
            )
            return self.form_invalid(form)

        organizacion = getattr(getattr(self.request.user, "perfil", None), "organizacion", None)

        estado_map = {key: key for key, _ in WorkOrder.ESTADOS}
        estado_map.update({label.lower(): key for key, label in WorkOrder.ESTADOS})
        prioridad_map = {key: key for key, _ in WorkOrder.PRIORIDADES}
        prioridad_map.update({label.lower(): key for key, label in WorkOrder.PRIORIDADES})

        errores = []
        filas = []
        total_filas = len(df)
        messages.info(
            self.request,
            f"Archivo leído correctamente. Filas detectadas: {total_filas}.",
        )


        def clean_text(valor):
            if valor is None:
                return ""
            if isinstance(valor, float) and pd.isna(valor):
                return ""
            if pd.isna(valor):
                return ""
            if isinstance(valor, str):
                return valor.strip()
            return str(valor).strip()

        for index, row in df.iterrows():
            fila = index + 2
            titulo = clean_text(row.get("titulo"))
            if not titulo:
                errores.append(f"Fila {fila}: el título es obligatorio.")
                continue

            equipo_codigo = clean_text(row.get("equipo_codigo"))
            equipo_tag = clean_text(row.get("equipo_tag"))
            equipo = None
            if equipo_codigo:
                equipo_qs = NodoActivo.objects.filter(codigo=equipo_codigo)
                if organizacion:
                    equipo_qs = equipo_qs.filter(organizacion=organizacion)
                equipo = equipo_qs.first()
            if not equipo and equipo_tag:
                equipo_qs = NodoActivo.objects.filter(tag=equipo_tag)
                if organizacion:
                    equipo_qs = equipo_qs.filter(organizacion=organizacion)
                equipo = equipo_qs.first()
            if not equipo:
                errores.append(
                    f"Fila {fila}: equipo no encontrado (usa equipo_codigo o equipo_tag)."
                )
                continue

            responsable = None
            responsable_identificacion = clean_text(
                row.get("responsable_identificacion")
            )
            if responsable_identificacion:
                responsable_qs = TecnicoOperativo.objects.filter(
                    numero_identificacion=responsable_identificacion,
                )
                if organizacion:
                    responsable_qs = responsable_qs.filter(perfil=organizacion)
                responsable = responsable_qs.first()
                if not responsable:
                    errores.append(
                        f"Fila {fila}: responsable no encontrado ({responsable_identificacion})."
                    )
                    continue

            actividad = None
            actividad_nombre = clean_text(row.get("actividad"))
            if actividad_nombre:
                actividad = ActividadNovedad.objects.filter(
                    nombre__iexact=actividad_nombre
                ).first()
                if not actividad:
                    errores.append(
                        f"Fila {fila}: actividad no encontrada ({actividad_nombre})."
                    )
                    continue

            estado_raw = clean_text(row.get("estado")).lower()
            if estado_raw:
                estado = estado_map.get(estado_raw)
                if not estado:
                    errores.append(
                        f"Fila {fila}: estado inválido ({estado_raw})."
                    )
                    continue
            else:
                 estado = "reportada"

            prioridad_raw = clean_text(row.get("prioridad")).lower()
            if prioridad_raw:
                prioridad = prioridad_map.get(prioridad_raw)
                if not prioridad:
                    errores.append(
                        f"Fila {fila}: prioridad inválida ({prioridad_raw})."
                    )
                    continue
            else:
                prioridad = "media"

            def parse_fecha(valor, campo):
                if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                    return None
                try:
                    return pd.to_datetime(valor).date()
                except Exception:
                    errores.append(f"Fila {fila}: fecha inválida en {campo}.")
                    return None

            fecha_programada = parse_fecha(row.get("fecha_programada"), "fecha_programada")
            if fecha_programada is None and any(
                msg.startswith(f"Fila {fila}: fecha inválida")
                for msg in errores
            ):
                continue

            fecha_cierre = parse_fecha(
                row.get("fecha_cierre_compromiso"), "fecha_cierre_compromiso"
            )
            if fecha_cierre is None and any(
                msg.startswith(f"Fila {fila}: fecha inválida")
                for msg in errores
            ):
                continue

            descripcion = clean_text(row.get("descripcion"))

            filas.append(
                {
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "equipo": equipo,
                    "responsable": responsable,
                    "actividad": actividad,
                    "prioridad": prioridad,
                    "estado": estado,
                    "fecha_programada": fecha_programada,
                    "fecha_cierre_compromiso": fecha_cierre,
                }
            )

        if errores:
            messages.error(
                self.request,
                "No pudimos importar porque hay errores en el archivo.",
            )
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    errores=errores,
                    resumen={
                        "total": total_filas,
                        "validas": len(filas),
                        "con_errores": len(errores),
                    },
                )
            )

        with transaction.atomic():
            for fila in filas:
                orden = WorkOrder.objects.create(**fila)
                WorkOrderEvento.objects.create(
                    orden=orden,
                    estado=orden.estado,
                    descripcion="Orden importada desde carga masiva",
                    creado_por=self.request.user,
                )

        messages.success(
            self.request,
            f"Importamos {len(filas)} órdenes de trabajo correctamente.",
        )
        return redirect("ot:orden_list")
    
class WorkOrderBulkTemplateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        organizacion = getattr(getattr(request.user, "perfil", None), "organizacion", None)
        if not organizacion:
            messages.error(request, "No encontramos la organización del usuario.")
            return redirect("ot:orden_carga_masiva")

        orden = (
            WorkOrder.objects.select_related("equipo", "responsable", "actividad")
            .filter(equipo__organizacion=organizacion)
            .order_by("-fecha_creacion")
            .first()
        )

        columnas = [
            "titulo",
            "equipo_codigo",
            "equipo_tag",
            "descripcion",
            "responsable_nombre",
            "actividad",
            "estado",
            "prioridad",
            "fecha_programada",
            "fecha_cierre_compromiso",
        ]

        plantilla_df = pd.DataFrame([{col: "" for col in columnas}])

        ejemplo_data = {
            "titulo": orden.titulo if orden else "Ejemplo OT",
            "equipo_codigo": orden.equipo.codigo if orden and orden.equipo else "",
            "equipo_tag": orden.equipo.tag if orden and orden.equipo else "",
            "descripcion": orden.descripcion if orden else "Descripción de referencia",
             "responsable_nombre": (
                orden.responsable.nombre_display if orden and orden.responsable else ""
            ),
            "actividad": orden.actividad.nombre if orden and orden.actividad else "",
             "estado": orden.estado if orden else "reportada",
            "prioridad": orden.prioridad if orden else "media",
            "fecha_programada": (
                orden.fecha_programada.isoformat() if orden and orden.fecha_programada else ""
            ),
            "fecha_cierre_compromiso": (
                orden.fecha_cierre_compromiso.isoformat() if orden and orden.fecha_cierre_compromiso else ""
            ),
        }

        ejemplo_df = pd.DataFrame([ejemplo_data])

        guia_df = pd.DataFrame(
            [
                {
                    "campo": "estado",
                    "valores": "reportada, por_iniciar, en_ejecucion, en_espera, finalizada, cancelada",
                },
                {"campo": "prioridad", "valores": "alta, media, baja"},
                {"campo": "fecha_programada", "valores": "YYYY-MM-DD"},
                {"campo": "fecha_cierre_compromiso", "valores": "YYYY-MM-DD"},
            ]
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            plantilla_df.to_excel(writer, index=False, sheet_name="plantilla")
            ejemplo_df.to_excel(writer, index=False, sheet_name="ejemplo")
            guia_df.to_excel(writer, index=False, sheet_name="guia")
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=plantilla_ot.xlsx"
        return response

def actualizar_estado(request, pk):
    orden = get_object_or_404(WorkOrder, pk=pk)
    if request.method != "POST":
        return redirect("ot:orden_detalle", pk=pk)

    form = WorkOrderEstadoForm(request.POST, request.FILES)
    if form.is_valid():
        nuevo_estado = form.cleaned_data["estado"]
        nota = form.cleaned_data["nota"]
        adjuntos = form.cleaned_data.get("adjuntos", [])
        cambios = []

        if nuevo_estado != orden.estado:
            orden.estado = nuevo_estado
            cambios.append("Estado actualizado.")

        if cambios:
            orden.save(update_fields=["estado", "fecha_actualizacion"])

        if nota or cambios or adjuntos:
            descripcion = nota or "Estado actualizado."
            if not nota and adjuntos and not cambios:
                descripcion = "Registro de archivos."
            evento = WorkOrderEvento.objects.create(
                orden=orden,
                estado=orden.estado,
                descripcion=descripcion,
                creado_por=request.user if request.user.is_authenticated else None,
            )
            for archivo in adjuntos:
                WorkOrderEventoFoto.objects.create(
                    evento=evento,
                    imagen=archivo,
                    creado_por=request.user if request.user.is_authenticated else None,
                )
            messages.success(request, "Movimos la OT y registramos la actividad.")
        else:
            messages.info(request, "No registramos cambios porque el estado es el mismo.")

    else:
        messages.error(request, "No pudimos actualizar el estado. Revisa el formulario.")

    return redirect("ot:orden_detalle", pk=pk)
