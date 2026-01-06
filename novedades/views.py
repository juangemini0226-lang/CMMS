import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CampoHijoForm,
    CampoPadreForm,
    NovedadDetalleFormSet,
    NovedadForm,
    SubopcionCampoForm,
)
from .models import CampoHijo, CampoPadre, Novedad, NovedadDetalle, SubopcionCampo


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
    try:
        filtro_dia = date.fromisoformat(dia) if dia else date.today()
    except ValueError:
        filtro_dia = date.today()
    novedades = (
        Novedad.objects.filter(fecha=filtro_dia)
        .select_related("equipo")
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=NovedadDetalle.objects.select_related(
                    "campo_padre", "campo_hijo", "subopcion"
                ),
            ),
        )
        .order_by("-id")
    )
    return render(
        request,
        "novedades/novedad_list.html",
        {"novedades": novedades, "dia": filtro_dia},
    )


@login_required
def crear_novedad(request):
    if request.method == "POST":
        form = NovedadForm(request.POST)
        formset = NovedadDetalleFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            novedad = form.save()
            detalles = formset.save(commit=False)
            for detalle in detalles:
                detalle.novedad = novedad
                detalle.save()
            messages.success(request, "Novedad registrada correctamente.")
            return redirect("novedades:novedad_detalle", pk=novedad.pk)
    else:
        form = NovedadForm()
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
        Novedad.objects.select_related("equipo").prefetch_related(
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
