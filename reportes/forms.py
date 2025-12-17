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
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class CargaDocumentoForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=[('reporte', 'Reporte'), ('orden', 'Orden de trabajo')],
        label="¿Qué deseas cargar?",
        widget=forms.RadioSelect(attrs={'class': 'tipo-opcion'})
    )
    descripcion = forms.CharField(
        label="Descripción breve (opcional)",
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Añade contexto, responsables o rango de fechas.'
        })
    )
    archivos = forms.FileField(
        label="Arrastra o selecciona tus archivos",
        widget=MultipleFileInput(attrs={
            'multiple': True,
            'class': 'form-control file-input',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.csv,.jpg,.jpeg,.png'
        })
    )

    def clean_archivos(self):
        archivos = self.files.getlist('archivos')
        if not archivos:
            raise forms.ValidationError("Debes seleccionar al menos un archivo.")
        return archivos