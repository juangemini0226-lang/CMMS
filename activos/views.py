from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, Q

from .models import (
    Organizacion,
    NivelJerarquia,
    NodoActivo,
    ClaseEquipoISO14224,
    PlantillaActivo,
    DocumentoActivo,
    FamiliaActivo,
    DependenciaActivo,
)
from .utils.manejador_excel import ImportadorExcelActivos
import json

from .forms import (
    SeleccionFamiliaForm,
    SeleccionActivoForm,
    DependenciaActivoForm,
    FamiliaActivoForm,
)


# ========================================
# VISTAS PRINCIPALES
# ========================================

@login_required
def gestionar_familias(request):
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de gestionar familias de activos.')
        return redirect('activos:dashboard_activos')

    familias = FamiliaActivo.objects.filter(
        Q(organizacion=organizacion) | Q(organizacion__isnull=True)
    ).annotate(
        total_activos=Count('activos', distinct=True),
        total_dependencias=Count('activos__dependencias', distinct=True),
    ).order_by('nombre')

    if request.method == 'POST':
        form = FamiliaActivoForm(request.POST)
        if form.is_valid():
            familia = form.save(commit=False)
            familia.organizacion = organizacion
            familia.save()
            messages.success(request, f'Familia "{familia.nombre}" creada correctamente.')
            return redirect('activos:gestionar_familias')
    else:
        form = FamiliaActivoForm()

    context = {
        'form': form,
        'familias': familias,
        'organizacion': organizacion,
    }
    return render(request, 'activos/gestionar_familias.html', context)


@login_required
def seleccionar_familia(request):
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de seleccionar familias.')
        return redirect('activos:dashboard_activos')

    familias_disponibles = FamiliaActivo.objects.filter(
        Q(organizacion=organizacion) | Q(organizacion__isnull=True)
    ).order_by('nombre')

    if request.method == 'POST':
        form = SeleccionFamiliaForm(request.POST, organizacion=organizacion)
        if form.is_valid():
            familia = form.cleaned_data['familia']
            return redirect('activos:seleccionar_activo', familia_id=familia.id)
    else:
        form = SeleccionFamiliaForm(organizacion=organizacion)

    if not familias_disponibles.exists() and request.method != 'POST':
        messages.info(
            request,
            'No hay familias registradas aún. Cree una nueva desde el menú "Familias".',
        )

    return render(
        request,
        'activos/seleccionar_familia.html',
        {
            'form': form,
            'familias_disponibles': familias_disponibles,
            'organizacion': organizacion,
        },
    )

@login_required
def seleccionar_activo(request, familia_id):
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de gestionar dependencias.')
        return redirect('activos:dashboard_activos')

    familia = get_object_or_404(
        FamiliaActivo.objects.filter(
            Q(organizacion=organizacion) | Q(organizacion__isnull=True)
        ),
        pk=familia_id,
    )
    total_activos_familia = NodoActivo.objects.filter(
        familia=familia,
        organizacion=organizacion,
    ).count()
    search_query = request.GET.get('q', '').strip()

    if request.method == 'POST':
        form = SeleccionActivoForm(
            familia=familia,
            organizacion=organizacion,
            search_query=search_query,
            data=request.POST,
        )
        if form.is_valid():
            activo = form.cleaned_data['activo']
            return redirect('activos:lista_dependencias', activo_id=activo.id)
    else:
        form = SeleccionActivoForm(
            familia=familia,
            organizacion=organizacion,
            search_query=search_query,
        )

    activos_disponibles = form.fields['activo'].queryset
    if (
        not activos_disponibles.exists()
        and request.method != 'POST'
        and not search_query
        and total_activos_familia == 0
    ):
        messages.info(
            request,
            'La familia seleccionada aún no tiene activos asociados. Registre activos de esta familia para continuar.',
        )

    return render(
        request,
        'activos/seleccionar_activo.html',
        {
            'form': form,
            'familia': familia,
            'activos_disponibles': activos_disponibles,
            'search_query': search_query,
            'total_activos_familia': total_activos_familia,
        },
    )

@login_required
def lista_dependencias(request, activo_id):
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de gestionar dependencias.')
        return redirect('activos:dashboard_activos')

    activo = get_object_or_404(NodoActivo, pk=activo_id, organizacion=organizacion)
    dependencias = activo.dependencias.order_by('nombre')
    padre_activo = getattr(activo, 'parent', None)

    if request.method == 'POST':
        form = DependenciaActivoForm(request.POST)
        if form.is_valid():
            dependencia = form.save(commit=False)
            dependencia.activo_padre = activo
            try:
                dependencia.save()
            except IntegrityError:
                form.add_error('nombre', 'Ya existe una dependencia con este nombre para el activo.')
            else:
                messages.success(request, 'Dependencia registrada correctamente')
                return redirect('activos:lista_dependencias', activo_id=activo.id)
    else:
        form = DependenciaActivoForm()

    return render(request, 'activos/lista_dependencias.html', {
        'activo': activo,
        'dependencias': dependencias,
        'form': form,
        'requiere_familia': activo.familia is None,
        'padre_activo': padre_activo,
    })

def dashboard_activos(request):
    """Dashboard principal de activos"""
    # Obtener organización del usuario (ajustar según tu modelo de usuario)
    # Por ahora asumimos que hay una organización
    try:
        organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    except Organizacion.DoesNotExist:
        return redirect('activos:crear_organizacion')
    
    # Estadísticas
    total_activos = NodoActivo.objects.filter(organizacion=organizacion).count()
    activos_activos = NodoActivo.objects.filter(
        organizacion=organizacion, 
        estado='activo'
    ).count()
    activos_criticos = NodoActivo.objects.filter(
        organizacion=organizacion,
        criticidad='alta'
    ).count()
    
    # Activos por nivel
    activos_por_nivel = NodoActivo.objects.filter(
        organizacion=organizacion
    ).values(
        'nivel_jerarquia__nombre_nivel'
    ).annotate(
        total=Count('id')
    )
    
    context = {
        'organizacion': organizacion,
        'total_activos': total_activos,
        'activos_activos': activos_activos,
        'activos_criticos': activos_criticos,
        'activos_por_nivel': activos_por_nivel,
    }
    
    return render(request, 'activos/dashboard.html', context)


@login_required
def configurar_jerarquia(request):
    """Vista para configurar la jerarquía de la organización"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    niveles = NivelJerarquia.objects.filter(organizacion=organizacion).order_by('numero_nivel')
    
    if request.method == 'POST':
        # Procesar formulario de configuración
        # Implementar según necesidades específicas
        messages.success(request, 'Jerarquía configurada correctamente')
        return redirect('activos:configurar_jerarquia')
    
    context = {
        'organizacion': organizacion,
        'niveles': niveles,
    }
    
    return render(request, 'activos/configurar_jerarquia.html', context)


@login_required
def vista_arbol_activos(request):
    """Vista del árbol interactivo de activos"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    
    # Obtener filtros
    nivel_id = request.GET.get('nivel')
    estado = request.GET.get('estado')
    busqueda = request.GET.get('q')
    
    # Query base
    activos = NodoActivo.objects.filter(
        organizacion=organizacion
    ).select_related(
        'nivel_jerarquia', 'parent'
    ).with_tree_fields()
    
    # Aplicar filtros
    if nivel_id:
        activos = NodoActivo.objects.filter(organizacion=organizacion,
        nivel_jerarquia_id=nivel_id
    ).select_related(
        'nivel_jerarquia', 'parent'
    )
    else:
        activos = NodoActivo.objects.filter(
        organizacion=organizacion
    ).select_related(
        'nivel_jerarquia', 'parent'
    ).with_tree_fields()
    if estado:
        activos = activos.filter(estado=estado)
    if busqueda:
        activos = activos.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo__icontains=busqueda) |
            Q(tag__icontains=busqueda)
        )
    
    # Niveles para filtro
    niveles = NivelJerarquia.objects.filter(organizacion=organizacion)
    
    context = {
        'organizacion': organizacion,
        'activos': activos,
        'niveles': niveles,
        'nivel_seleccionado': nivel_id,
        'estado_seleccionado': estado,
        'busqueda': busqueda,
    }
    
    return render(request, 'activos/arbol_activos.html', context)



@login_required
def crear_activo(request, padre_id=None):
    """Crear nuevo activo"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica

    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de crear activos.')
        return redirect('activos:dashboard_activos')

    padre = None
    if padre_id:
        padre = get_object_or_404(NodoActivo, id=padre_id, organizacion=organizacion)
    
    if request.method == 'POST':
        # Procesar formulario
        nivel_id = request.POST.get('nivel_jerarquia')
        nivel = get_object_or_404(NivelJerarquia, id=nivel_id, organizacion=organizacion)
        
        familia = None
        familia_id = request.POST.get('familia')
        if familia_id:
            familia = get_object_or_404(
                FamiliaActivo.objects.filter(
                    Q(organizacion=organizacion) | Q(organizacion__isnull=True)
                ),
                id=familia_id,
            )

        activo = NodoActivo.objects.create(
            organizacion=organizacion,
            nivel_jerarquia=nivel,
            parent=padre,
            nombre=request.POST.get('nombre'),
            codigo=request.POST.get('codigo'),
            descripcion=request.POST.get('descripcion', ''),
            fabricante=request.POST.get('fabricante', ''),
            modelo=request.POST.get('modelo', ''),
            numero_serie=request.POST.get('numero_serie', ''),
            estado=request.POST.get('estado', 'activo'),
            criticidad=request.POST.get('criticidad', ''),
            ubicacion_fisica=request.POST.get('ubicacion_fisica', ''),
            familia=familia,
            creado_por=request.user
        )

        messages.success(request, f'Activo "{activo.nombre}" creado exitosamente')
        return redirect('activos:detalle_activo', activo_id=activo.id)

    niveles = NivelJerarquia.objects.filter(organizacion=organizacion)
    familias = FamiliaActivo.objects.filter(
        Q(organizacion=organizacion) | Q(organizacion__isnull=True)
    ).order_by('nombre')

    context = {
        'padre': padre,
        'niveles': niveles,
        'organizacion': organizacion,
        'familias': familias,
    }

    return render(request, 'activos/crear_activo.html', context)


@login_required
def detalle_activo(request, activo_id):
    """Detalle de un activo"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    activo = get_object_or_404(
        NodoActivo, 
        id=activo_id, 
        organizacion=organizacion
    )
    
    # Obtener hijos
    hijos = activo.children.all()
    
    # Obtener documentos y dependencias
    documentos = activo.documentos.all()
    dependencias = activo.dependencias.order_by('nombre')

    context = {
        'activo': activo,
        'hijos': hijos,
        'documentos': documentos,
        'dependencias': dependencias,
    }

    return render(request, 'activos/detalle_activo.html', context)


@login_required
def editar_activo(request, activo_id):
    """Editar activo existente"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica

    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de editar activos.')
        return redirect('activos:dashboard_activos')

    activo = get_object_or_404(
        NodoActivo,
        id=activo_id,
        organizacion=organizacion
    )
    
    if request.method == 'POST':
        activo.nombre = request.POST.get('nombre')
        activo.descripcion = request.POST.get('descripcion', '')
        activo.fabricante = request.POST.get('fabricante', '')
        activo.modelo = request.POST.get('modelo', '')
        activo.numero_serie = request.POST.get('numero_serie', '')
        activo.estado = request.POST.get('estado')
        activo.criticidad = request.POST.get('criticidad', '')
        activo.ubicacion_fisica = request.POST.get('ubicacion_fisica', '')
        familia_id = request.POST.get('familia')
        if familia_id:
            activo.familia = get_object_or_404(
                FamiliaActivo.objects.filter(
                    Q(organizacion=organizacion) | Q(organizacion__isnull=True)
                ),
                id=familia_id,
            )
        else:
            activo.familia = None

        activo.save()

        messages.success(request, 'Activo actualizado exitosamente')
        return redirect('activos:detalle_activo', activo_id=activo.id)

    familias = FamiliaActivo.objects.filter(
        Q(organizacion=organizacion) | Q(organizacion__isnull=True)
    ).order_by('nombre')

    context = {
        'activo': activo,
        'familias': familias,
    }

    return render(request, 'activos/editar_activo.html', context)
@login_required
def eliminar_activo(request, activo_id):
    """Eliminar activo"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    activo = get_object_or_404(
        NodoActivo, 
        id=activo_id, 
        organizacion=organizacion
    )
    
    if request.method == 'POST':
        nombre = activo.nombre
        activo.delete()
        messages.success(request, f'Activo "{nombre}" eliminado exitosamente')
        return redirect('activos:vista_arbol_activos')
    
    context = {
        'activo': activo,
    }
    
    return render(request, 'activos/eliminar_activo.html', context)


# ========================================
# IMPORTACIÓN/EXPORTACIÓN EXCEL
# ========================================

@login_required
def importar_excel(request):
    """Importar activos desde Excel"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo_excel = request.FILES['archivo_excel']
        
        # Guardar archivo temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in archivo_excel.chunks():
                tmp.write(chunk)
            ruta_temporal = tmp.name
        
        # Importar
        try:
            importador = ImportadorExcelActivos(organizacion)
            resultado = importador.importar_desde_excel(ruta_temporal)
            
            if resultado['errores']:
                for error in resultado['errores']:
                    messages.warning(request, error)
            
            messages.success(
                request, 
                f"Importación completada: {resultado['exitosos']} activos creados"
            )
            
        except Exception as e:
            messages.error(request, f'Error al importar: {str(e)}')
        
        return redirect('activos:vista_arbol_activos')
    
    return render(request, 'activos/importar_excel.html')


@login_required
def exportar_excel(request):
    """Exportar activos a Excel"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    
    import tempfile
    import os
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        ruta_temporal = tmp.name
    
    # Exportar
    importador = ImportadorExcelActivos(organizacion)
    importador.exportar_a_excel(ruta_temporal)
    
    # Leer y enviar archivo
    with open(ruta_temporal, 'rb') as f:
        response = HttpResponse(
            f.read(), 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="activos_{organizacion.codigo}.xlsx"'
    
    # Limpiar archivo temporal
    os.unlink(ruta_temporal)
    
    return response


@login_required
def descargar_plantilla_excel(request):
    """Descargar plantilla Excel para importación"""
    import pandas as pd
    import tempfile
    import os
    
    # Crear plantilla
    datos_ejemplo = {
        'nivel': [1, 2, 2, 3, 3],
        'nombre': ['Planta Principal', 'Área 1', 'Área 2', 'Bomba 001', 'Bomba 002'],
        'codigo': ['P001', 'A001', 'A002', 'B001', 'B002'],
        'padre': ['', 'P001', 'P001', 'A001', 'A001'],
        'descripcion': ['', '', '', 'Bomba centrífuga', 'Bomba centrífuga'],
        'fabricante': ['', '', '', 'Manufacturer A', 'Manufacturer A'],
        'modelo': ['', '', '', 'Model X', 'Model X'],
        'serie': ['', '', '', '12345', '12346'],
    }
    
    df = pd.DataFrame(datos_ejemplo)
    
    # Guardar en temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        ruta_temporal = tmp.name
    
    df.to_excel(ruta_temporal, index=False, engine='openpyxl')
    
    # Enviar archivo
    with open(ruta_temporal, 'rb') as f:
        response = HttpResponse(
            f.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="plantilla_activos.xlsx"'
    
    # Limpiar
    os.unlink(ruta_temporal)
    
    return response


# ========================================
# API JSON (para interfaces interactivas)
# ========================================

@login_required
def api_arbol_activos(request):
    """API JSON para árbol de activos (para JavaScript)"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    
    activos = NodoActivo.objects.filter(
        organizacion=organizacion
    ).select_related('nivel_jerarquia', 'parent')
    
    def construir_nodo(activo):
        return {
            'id': activo.id,
            'nombre': activo.nombre,
            'codigo': activo.codigo,
            'tag': activo.tag,
            'nivel': activo.nivel_jerarquia.nombre_nivel,
            'estado': activo.estado,
            'criticidad': activo.criticidad,
            'parent_id': activo.parent.id if activo.parent else None,
            'hijos': [construir_nodo(hijo) for hijo in activo.children.all()]
        }
    
    # Obtener nodos raíz
    raices = activos.filter(parent__isnull=True)
    arbol = [construir_nodo(raiz) for raiz in raices]
    
    return JsonResponse({'arbol': arbol})


@login_required
def api_generar_tag(request):
    """API para generar TAG automático"""
    if request.method == 'POST':
        data = json.loads(request.body)
        nivel_id = data.get('nivel_id')
        codigo = data.get('codigo')
        padre_id = data.get('padre_id')
        
        organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
        nivel = get_object_or_404(NivelJerarquia, id=nivel_id, organizacion=organizacion)
        
        # Crear activo temporal para generar TAG
        activo_temp = NodoActivo(
            organizacion=organizacion,
            nivel_jerarquia=nivel,
            codigo=codigo,
            nombre='temp',
            creado_por=request.user
        )
        
        if padre_id:
            activo_temp.parent = get_object_or_404(NodoActivo, id=padre_id)
        
        tag_generado = activo_temp.generar_tag()
        
        return JsonResponse({'tag': tag_generado})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)
