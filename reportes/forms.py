from django import forms

class SeleccionReporteForm(forms.Form):
    TIPO_REPORTE_CHOICES = [
        ('activos', 'Reporte de Activos'),
        ('taxonomia', 'Reporte de Taxonomía ISO'),
    ]
    tipo_reporte = forms.ChoiceField(
        choices=TIPO_REPORTE_CHOICES, 
        label="Tipo de Reporte",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
