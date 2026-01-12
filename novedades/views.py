import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from activos.models import NodoActivo
from ot.models import WorkOrder
from django.utils import timezone

from .forms import (
    CampoHijoForm,
    CampoPadreForm,
    NovedadDetalleFormSet,
    NovedadForm,
    SubopcionCampoForm,
)
from .models import (
    ActividadNovedad,
     AtencionPlantaDetalle,
    CampoHijo,
    CampoPadre,
    Novedad,
    NovedadDetalle,
    SubopcionCampo,
)


@login_required
def configuracion_campos(request):
    campo_padre_form = CampoPadreForm(prefix="padre")
    campo_hijo_form = CampoHijoForm(prefix="hijo")
    subopcion_form = SubopcionCampoForm(prefix="subopcion")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "padre":
            campo_padre_form = CampoPadreForm(request.POST, prefix="padre")
            if campo_padre_form.is_valid():
                campo_padre_form.save()
                messages.success(request, "Campo padre creado correctamente.")
                return redirect("novedades:configuracion_campos")
        elif action == "hijo":
            campo_hijo_form = CampoHijoForm(request.POST, prefix="hijo")
            if campo_hijo_form.is_valid():
                campo_hijo_form.save()
                messages.success(request, "Campo hijo creado correctamente.")
                return redirect("novedades:configuracion_campos")
        elif action == "subopcion":
            subopcion_form = SubopcionCampoForm(request.POST, prefix="subopcion")
            if subopcion_form.is_valid():
                subopcion_form.save()
                messages.success(request, "Subopción agregada correctamente.")
                return redirect("novedades:configuracion_campos")

    campos = CampoPadre.objects.prefetch_related(
        Prefetch(
            "hijos",
            queryset=CampoHijo.objects.prefetch_related("subopciones").order_by(
                "nombre"
            ),
        )
    ).order_by("nombre")
    return render(
        request,
        "novedades/configuracion_campos.html",
        {
            "campo_padre_form": campo_padre_form,
            "campo_hijo_form": campo_hijo_form,
            "subopcion_form": subopcion_form,
            "campos": campos,
        },
    )


@login_required
def editar_campo_padre(request, pk):
    campo_padre = get_object_or_404(CampoPadre, pk=pk)
    if request.method == "POST":
        form = CampoPadreForm(request.POST, instance=campo_padre)
        if form.is_valid():
            form.save()
            messages.success(request, "Campo padre actualizado.")
            return redirect("novedades:configuracion_campos")
    else:
        form = CampoPadreForm(instance=campo_padre)
    return render(
        request, "novedades/campo_form.html", {"form": form, "titulo": "Editar campo padre"}
    )


@login_required
def editar_campo_hijo(request, pk):
    campo_hijo = get_object_or_404(CampoHijo, pk=pk)
    if request.method == "POST":
        form = CampoHijoForm(request.POST, instance=campo_hijo)
        if form.is_valid():
            form.save()
            messages.success(request, "Campo hijo actualizado.")
            return redirect("novedades:configuracion_campos")
    else:
        form = CampoHijoForm(instance=campo_hijo)
    return render(
        request, "novedades/campo_form.html", {"form": form, "titulo": "Editar campo hijo"}
    )


@login_required
def editar_subopcion_campo(request, pk):
    subopcion = get_object_or_404(SubopcionCampo, pk=pk)
    if request.method == "POST":
        form = SubopcionCampoForm(request.POST, instance=subopcion)
        if form.is_valid():
            form.save()
            messages.success(request, "Subopción actualizada.")
            return redirect("novedades:configuracion_campos")
    else:
        form = SubopcionCampoForm(instance=subopcion)
    return render(
        request, "novedades/campo_form.html", {"form": form, "titulo": "Editar subopción"}
    )


@login_required
def lista_novedades(request):
    dia = request.GET.get("dia")
    desde_param = request.GET.get("desde") or dia
    hasta_param = request.GET.get("hasta") or dia
    estado = request.GET.get("estado") or ""
    actividad_id = request.GET.get("actividad") or ""
    equipo_id = request.GET.get("equipo") or ""
    con_ot = request.GET.get("con_ot") or ""

    def _parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    filtro_desde = _parse_date(desde_param) or timezone.localdate()
    filtro_hasta = _parse_date(hasta_param) or filtro_desde
    if filtro_desde > filtro_hasta:
        filtro_desde, filtro_hasta = filtro_hasta, filtro_desde

    novedades_qs = Novedad.objects.filter(fecha__range=(filtro_desde, filtro_hasta))
    if estado:
        novedades_qs = novedades_qs.filter(estado=estado)
    if actividad_id:
        novedades_qs = novedades_qs.filter(actividad_id=actividad_id)
    if equipo_id:
        novedades_qs = novedades_qs.filter(equipo_id=equipo_id)
    if con_ot == "si":
        novedades_qs = novedades_qs.filter(ordenes_trabajo__isnull=False)
    if con_ot == "no":
        novedades_qs = novedades_qs.filter(ordenes_trabajo__isnull=True)

    novedades = (
        novedades_qs.select_related("equipo", "actividad")
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=NovedadDetalle.objects.select_related(
                    "campo_padre", "campo_hijo", "subopcion"
                ),
            ),
            Prefetch(
                "ordenes_trabajo",
                queryset=WorkOrder.objects.select_related("equipo").order_by(
                    "-fecha_creacion"
                ),
            ),
        )
        .order_by("-fecha", "-id")
        .distinct()
    )

    estados = [{"id": key, "label": label} for key, label in Novedad.ESTADOS]
    agrupadas = {label: [] for _, label in Novedad.ESTADOS}
    for novedad in novedades:
        agrupadas[dict(Novedad.ESTADOS).get(novedad.estado, novedad.estado)].append(
            novedad
        )

    hoy = timezone.localdate()
    novedades_hoy = Novedad.objects.filter(fecha=hoy).count()
    ots_hoy = WorkOrder.objects.filter(fecha_creacion__date=hoy).count()
    return render(
        request,
        "novedades/novedad_list.html",
        {
            "agrupadas": agrupadas,
            "dia": filtro_desde,
            "desde": filtro_desde,
            "hasta": filtro_hasta,
            "estado_filtro": estado,
            "actividad_filtro": actividad_id,
            "equipo_filtro": equipo_id,
            "con_ot_filtro": con_ot,
            "estados": estados,
             "actividades": ActividadNovedad.visibles_para_novedades(),
            "equipos": NodoActivo.objects.order_by("nombre"),
            "novedades_total": novedades.count(),
            "novedades_hoy": novedades_hoy,
            "ots_hoy": ots_hoy,
        },
    )


@login_required
def crear_novedad(request):
    if request.method == "POST":
        form = NovedadForm(request.POST)
        formset = NovedadDetalleFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            novedad = form.save()
            detalles = formset.save(commit=False)
            tiempo_empleado_min = form.cleaned_data.get("tiempo_empleado_min")
            for detalle in detalles:
                detalle.novedad = novedad
                detalle.save()
                if tiempo_empleado_min is not None:
                    AtencionPlantaDetalle.objects.filter(
                        novedad_detalle_id=detalle.pk
                    ).update(tiempo_empleado_min=tiempo_empleado_min)
            messages.success(request, "Novedad registrada correctamente.")
            return redirect("novedades:novedad_detalle", pk=novedad.pk)
    else:
        form = NovedadForm(initial={"fecha": timezone.localdate()})
        formset = NovedadDetalleFormSet()

    hijos_json = json.dumps(
        list(
            CampoHijo.objects.filter(activo=True)
            .values("id", "padre_id", "nombre")
            .order_by("padre__nombre", "nombre")
        ),
        ensure_ascii=False,
    )
    subopciones_json = json.dumps(
        list(
            SubopcionCampo.objects.filter(campo_hijo__activo=True)
            .values("id", "campo_hijo_id", "nombre")
            .order_by("campo_hijo__padre__nombre", "campo_hijo__nombre", "nombre")
        ),
        ensure_ascii=False,
    )
    return render(
        request,
        "novedades/novedad_form.html",
        {
            "form": form,
            "formset": formset,
            "hijos_json": hijos_json,
            "subopciones_json": subopciones_json,
        },
    )


@login_required
def novedad_detalle(request, pk):
    novedad = get_object_or_404(
        Novedad.objects.select_related(
            "equipo", "actividad", "equipo_obligatorio_cumplimiento"
        ).prefetch_related(
            Prefetch(
                "detalles",
                queryset=NovedadDetalle.objects.select_related(
                    "campo_padre", "campo_hijo", "subopcion"
                ),
            ),
        ),
        pk=pk,
    )
    return render(request, "novedades/novedad_detalle.html", {"novedad": novedad})
