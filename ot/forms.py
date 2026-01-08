from django import forms

from novedades.models import ActividadNovedad, Novedad

from .models import WorkOrder


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = [
            "titulo",
            "descripcion",
            "equipo",
            "responsable",
            "actividad",
            "prioridad",
            "estado",
            "fecha_programada",
            "fecha_cierre_compromiso",
            "novedad_origen",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_programada": forms.DateInput(attrs={"type": "date"}),
            "fecha_cierre_compromiso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        novedad_qs = Novedad.objects.filter(estado="pendiente")
        if self.instance.pk and self.instance.novedad_origen:
            novedad_qs = novedad_qs | Novedad.objects.filter(
                pk=self.instance.novedad_origen_id
            )
        self.fields["novedad_origen"].queryset = novedad_qs.select_related("equipo")
        self.fields["novedad_origen"].required = False
        self.fields["actividad"].queryset = ActividadNovedad.objects.filter(activo=True)
        self.fields["actividad"].required = False
        self.fields["titulo"].widget.attrs.update({"placeholder": "Reparación, inspección, ajuste..."})
        self.fields["descripcion"].widget.attrs.update(
            {"placeholder": "Agrega alcance, riesgos, materiales o pasos clave."}
        )

class WorkOrderEstadoForm(forms.Form):
    estado = forms.ChoiceField(label="Mover a estado", choices=WorkOrder.ESTADOS)
    nota = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Notas, riesgos, avances o pendientes."}
        ),
        label="Comentario",
    )