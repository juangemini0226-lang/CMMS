from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Case, IntegerField, When
from django.shortcuts import redirect, render

from ot.models import WorkOrder
from personal.models import TecnicoOperativo


def home(request):
    tecnico_actual = None
    if request.user.is_authenticated:
        try:
            tecnico_actual = request.user.tecnico_operativo
        except TecnicoOperativo.DoesNotExist:
            tecnico_actual = None

    return render(request, "home.html", {"tecnico_actual": tecnico_actual})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


@login_required
def panel_tecnico(request):
    try:
        tecnico = request.user.tecnico_operativo
    except TecnicoOperativo.DoesNotExist:
        messages.error(
            request,
            "El panel de técnicos está limitado a usuarios identificados como técnicos.",
        )
        return redirect("home")

    prioridad_orden = Case(
        When(prioridad="alta", then=0),
        When(prioridad="media", then=1),
        default=2,
        output_field=IntegerField(),
    )

    ordenes_pendientes = (
        WorkOrder.objects.filter(
            responsable=tecnico, estado__in=["pendiente", "por_iniciar"]
        )
        .select_related("equipo", "responsable__user")
        .order_by(prioridad_orden, "-fecha_creacion")
    )
    ordenes_activas = (
        WorkOrder.objects.filter(responsable=tecnico, estado__in=["en_ejecucion", "en_espera"])
        .select_related("equipo", "responsable__user")
        .order_by("-fecha_actualizacion", "-fecha_creacion")
    )

    contexto = {
        "tecnico": tecnico,
        "ordenes_pendientes": ordenes_pendientes,
        "ordenes_activas": ordenes_activas,
        "resumen_ot": {
            "total": ordenes_pendientes.count() + ordenes_activas.count(),
            "pendientes": ordenes_pendientes.count(),
            "activas": ordenes_activas.count(),
        },
    }

    return render(request, "tecnico_panel.html", contexto)
