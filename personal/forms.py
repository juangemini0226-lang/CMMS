from django import forms
from django.utils import timezone

from .models import Ausencia, TecnicoOperativo, Turno


class BaseStyledModelForm(forms.ModelForm):
    """Añade clases tailwind/bootstrap-like para inputs modernos."""

    class Meta:
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_classes} form-control-modern".strip()
            if field.widget.__class__.__name__ in {"Textarea", "TextInput"}:
                field.widget.attrs.setdefault("rows", 3)


class TurnoForm(BaseStyledModelForm):
    fecha_inicio = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Inicio",
    )
    fecha_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Fin",
    )

    class Meta:
        model = Turno
        fields = [
            "nombre",
            "descripcion",
            "fecha_inicio",
            "fecha_fin",
            "color",
            "tecnicos",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "color": forms.TextInput(attrs={"type": "color"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error("fecha_fin", "La fecha de finalización debe ser mayor o igual que la de inicio.")
        return cleaned_data


class AusenciaForm(BaseStyledModelForm):
    class Meta:
        model = Ausencia
        fields = [
            "tecnico",
            "tipo",
            "fecha_inicio",
            "fecha_fin",
            "motivo",
            "estado",
            "turno_relacionado",
            "aprobado_por",
        ]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "motivo": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error("fecha_fin", "La fecha de finalización debe ser mayor o igual que la de inicio.")
        return cleaned_data