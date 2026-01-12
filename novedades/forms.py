import unicodedata
from django import forms
from django.forms import inlineformset_factory

from activos.models import NodoActivo

from .models import (
    ActividadNovedad,
    CampoHijo,
    CampoPadre,
    Novedad,
    NovedadDetalle,
    SubopcionCampo,
)


class CampoPadreForm(forms.ModelForm):
    class Meta:
        model = CampoPadre
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Sistema de inyección, Refrigeración",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Descripción y alcance del campo padre",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CampoHijoForm(forms.ModelForm):
    class Meta:
        model = CampoHijo
        fields = ["padre", "nombre", "descripcion", "activo"]
        widgets = {
            "padre": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del campo hijo",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Detalle o uso del campo hijo",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SubopcionCampoForm(forms.ModelForm):
    class Meta:
        model = SubopcionCampo
        fields = ["campo_hijo", "nombre", "codigo", "descripcion"]
        widgets = {
            "campo_hijo": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la subopción",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Referencia o código",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Notas para la subopción",
                }
            ),
        }


class NovedadForm(forms.ModelForm):
    actividad = forms.ModelChoiceField(
        queryset=ActividadNovedad.visibles_para_novedades(),
        label="Actividad",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    tiempo_empleado_min = forms.IntegerField(
        required=False,
        min_value=0,
        label="Tiempo empleado (min)",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej: 45",
                "min": 0,
            }
        ),
    )
    equipo = forms.ModelChoiceField(
        queryset=NodoActivo.objects.order_by("nombre"),
        label="Equipo o molde",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Novedad
        fields = ["fecha", "actividad", "equipo", "estado", "descripcion"]
        widgets = {
            "fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción detallada de la novedad",
                }
            ),
            "estado": forms.RadioSelect(attrs={"class": "estado-radio"}),
        }
class NovedadDetalleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campo_padre"].queryset = CampoPadre.objects.filter(
            activo=True
        ).order_by("nombre")
        padre_id = self._get_field_value("campo_padre")
        hijo_id = self._get_field_value("campo_hijo")
        self.fields["campo_hijo"].queryset = (
            CampoHijo.objects.filter(activo=True, padre_id=padre_id)
            .select_related("padre")
            .order_by("nombre")
            if padre_id
            else CampoHijo.objects.none()
        )
        self.fields["subopcion"].queryset = (
            SubopcionCampo.objects.filter(campo_hijo_id=hijo_id)
            .select_related("campo_hijo", "campo_hijo__padre")
            .order_by("nombre")
            if hijo_id
            else SubopcionCampo.objects.none()
        )
        self.fields["subopcion"].required = False
        self.fields["evidencia"].required = False

    class Meta:
        model = NovedadDetalle
        fields = ["campo_padre", "campo_hijo", "subopcion", "comentario", "evidencia"]
        widgets = {
            "campo_padre": forms.Select(attrs={"class": "form-select detalle-padre"}),
            "campo_hijo": forms.Select(attrs={"class": "form-select detalle-hijo"}),
            "subopcion": forms.Select(
                attrs={"class": "form-select detalle-subopcion"}
            ),
            "comentario": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Comentario o aclaración",
                }
            ),
            "evidencia": forms.ClearableFileInput(
                attrs={"class": "form-control detalle-evidencia", "accept": "image/*"}
            ),
        }

    def _get_field_value(self, field_name):
        data_key = f"{self.prefix}-{field_name}" if self.prefix else field_name
        if data_key in self.data and self.data.get(data_key):
            try:
                return int(self.data.get(data_key))
            except (TypeError, ValueError):
                return None
        initial_value = self.initial.get(field_name)
        if initial_value:
            return getattr(initial_value, "id", initial_value)
        instance_value = getattr(self.instance, f"{field_name}_id", None)
        if instance_value:
            return instance_value
        return None

    def clean(self):
        cleaned_data = super().clean()
        padre = cleaned_data.get("campo_padre")
        hijo = cleaned_data.get("campo_hijo")
        subopcion = cleaned_data.get("subopcion")
        if hijo and padre and hijo.padre_id != padre.id:
            raise forms.ValidationError(
                "El campo hijo seleccionado no pertenece al campo padre elegido."
            )
        if subopcion and hijo and subopcion.campo_hijo_id != hijo.id:
            raise forms.ValidationError(
                "La subopción seleccionada no coincide con el campo hijo elegido."
            )
        return cleaned_data


NovedadDetalleFormSet = inlineformset_factory(
    Novedad,
    NovedadDetalle,
    form=NovedadDetalleForm,
    fields=["campo_padre", "campo_hijo", "subopcion", "comentario", "evidencia"],
    extra=1,
    can_delete=False,
    validate_min=False,
)
