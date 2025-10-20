from django import forms
from django.db.models import Q

from .models import DependenciaActivo, FamiliaActivo, NodoActivo


class FamiliaActivoForm(forms.ModelForm):
    class Meta:
        model = FamiliaActivo
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la familia'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SeleccionFamiliaForm(forms.Form):
    familia = forms.ModelChoiceField(
        queryset=FamiliaActivo.objects.none(),
        required=True,
        empty_label="Seleccione una familia",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, organizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = FamiliaActivo.objects.all()
        if organizacion is not None:
            queryset = queryset.filter(Q(organizacion=organizacion) | Q(organizacion__isnull=True))
        self.fields['familia'].queryset = queryset.order_by('nombre')


class SeleccionActivoForm(forms.Form):
    activo = forms.ModelChoiceField(
        queryset=NodoActivo.objects.none(),
        required=True,
        empty_label="Seleccione un activo",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, familia=None, organizacion=None, search_query=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if familia is not None:
            queryset = familia.activos.all()
            if organizacion is not None:
                queryset = queryset.filter(organizacion=organizacion)
            if search_query:
                queryset = queryset.filter(
                    Q(nombre__icontains=search_query)
                    | Q(codigo__icontains=search_query)
                    | Q(tag__icontains=search_query)
                )
            self.fields['activo'].queryset = queryset.order_by('nombre')
        else:
            self.fields['activo'].queryset = NodoActivo.objects.none()


class DependenciaActivoForm(forms.ModelForm):
    class Meta:
        model = DependenciaActivo
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del componente'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
        }


class NodoActivoForm(forms.ModelForm):
    familia = forms.ModelChoiceField(
        queryset=FamiliaActivo.objects.none(),
        required=False,
        empty_label="Seleccione una familia",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, organizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = FamiliaActivo.objects.all()
        if organizacion is not None:
            queryset = queryset.filter(Q(organizacion=organizacion) | Q(organizacion__isnull=True))
        self.fields['familia'].queryset = queryset.order_by('nombre')

    class Meta:
        model = NodoActivo
        fields = [
            'codigo',
            'nombre',
            'descripcion',
            'fabricante',
            'modelo',
            'numero_serie',
            'estado',
            'criticidad',
            'ubicacion_fisica',
            'familia',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código interno'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del activo'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'criticidad': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion_fisica': forms.TextInput(attrs={'class': 'form-control'}),
        }