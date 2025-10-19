from django import forms
from .models import FamiliaActivo, NodoActivo, DependenciaActivo

class FamiliaActivoForm(forms.ModelForm):
    class Meta:
        model = FamiliaActivo
        fields = ['nombre', 'descripcion']

class SeleccionFamiliaForm(forms.Form):
    familia = forms.ModelChoiceField(
        queryset=FamiliaActivo.objects.all(),
        required=True,
        empty_label="Seleccione una familia",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class SeleccionActivoForm(forms.Form):
    activo = forms.ModelChoiceField(
        queryset=NodoActivo.objects.none(),
        required=True,
        empty_label="Seleccione un activo",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, familia=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if familia:
            self.fields['activo'].queryset = NodoActivo.objects.filter(familia=familia)
        else:
            self.fields['activo'].queryset = NodoActivo.objects.none()

class DependenciaActivoForm(forms.ModelForm):
    class Meta:
        model = DependenciaActivo
        fields = ['nombre', 'descripcion']

class NodoActivoForm(forms.ModelForm):
    familia = forms.ModelChoiceField(
        queryset=FamiliaActivo.objects.all(),
        required=False,
        empty_label="Seleccione Familia",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = NodoActivo
        fields = [
            'codigo',
            'nombre',
            'estado',
            'criticidad',
            'ubicacion_fisica',
            'familia',  # agregar familia al formulario
            # otros campos relevantes...
        ]