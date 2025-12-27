import pandas as pd
import os
from django.core.exceptions import ValidationError
from activos.models import NodoActivo, NivelJerarquia, Organizacion

class ImportadorExcelActivos:
    """Maneja importación de activos desde Excel"""
    
    def __init__(self, organizacion, usuario=None):
        self.organizacion = organizacion
        self.usuario = usuario
    
    def importar_desde_excel(self, ruta_archivo):
        """Importa jerarquía de activos desde Excel"""
        if not self.organizacion:
            raise ValidationError("Se requiere una organización configurada para importar activos.")

        if not os.path.exists(ruta_archivo):
            raise ValidationError("El archivo de Excel no está disponible para importar.")

        df = pd.read_excel(ruta_archivo)
        
        # Validar columnas requeridas
        columnas_requeridas = ['nivel', 'nombre', 'codigo', 'padre']
        if not all(col in df.columns for col in columnas_requeridas):
            raise ValidationError(
                f"El archivo Excel debe contener las columnas: {', '.join(columnas_requeridas)}"
            )
        
        activos_creados = []
        errores = []
        
        # Procesar por niveles (de arriba hacia abajo)
        for numero_nivel in sorted(df['nivel'].unique()):
            datos_nivel = df[df['nivel'] == numero_nivel]
            
            for idx, fila in datos_nivel.iterrows():
                try:
                    activo = self._crear_activo_desde_fila(fila)
                    activos_creados.append(activo)
                except Exception as e:
                    errores.append(f"Fila {idx + 2}: {str(e)}")
        
        return {
            'exitosos': len(activos_creados),
            'errores': errores,
            'activos': activos_creados
        }
    
    def _crear_activo_desde_fila(self, fila):
        """Crea un activo desde una fila de Excel"""
        nivel_jerarquia = NivelJerarquia.objects.get(
            organizacion=self.organizacion,
            numero_nivel=fila['nivel']
        )
        
        # Buscar padre si existe
        padre = None
        if pd.notna(fila['padre']):
            padre = NodoActivo.objects.get(
                organizacion=self.organizacion,
                codigo=fila['padre']
            )
        
        # Crear activo
        activo = NodoActivo.objects.create(
            organizacion=self.organizacion,
            nivel_jerarquia=nivel_jerarquia,
            parent=padre,
            nombre=fila['nombre'],
            codigo=fila['codigo'],
            descripcion=fila.get('descripcion', ''),
            fabricante=fila.get('fabricante', ''),
            modelo=fila.get('modelo', ''),
            numero_serie=fila.get('serie', ''),
            creado_por=self.usuario or self.organizacion.creado_por
        )
        
        return activo
    
    def exportar_a_excel(self, ruta_salida):
        """Exporta jerarquía a Excel"""
        activos = NodoActivo.objects.filter(organizacion=self.organizacion)
        
        datos = []
        for activo in activos:
            datos.append({
                'TAG': activo.tag or '',
                'Nivel': activo.nivel_jerarquia.numero_nivel,
                'Tipo': activo.nivel_jerarquia.nombre_nivel,
                'Nombre': activo.nombre,
                'Código': activo.codigo,
                'Padre': activo.parent.codigo if activo.parent else '',
                'Ruta Completa': activo.obtener_ruta_completa(),
                'Fabricante': activo.fabricante,
                'Modelo': activo.modelo,
                'Serie': activo.numero_serie,
                'Estado': activo.get_estado_display(),
                'Criticidad': activo.get_criticidad_display(),
                'Fecha Instalación': activo.fecha_instalacion,
            })
        
        df = pd.DataFrame(datos)
        df.to_excel(ruta_salida, index=False, engine='openpyxl')
        
        return ruta_salida
