from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, QueryDict
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.text import slugify
from urllib.parse import urlencode

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
from novedades.models import Novedad
from ot.models import WorkOrder
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
def gestionar_taxonomia_iso(request):
    """Pantalla dedicada para crear y mantener la taxonomía ISO 14224 (niveles 6-9)."""
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de gestionar la taxonomía ISO 14224.')
        return redirect('activos:dashboard_activos')

    clases_qs = ClaseEquipoISO14224.objects.all().select_related('padre').order_by('nivel_taxonomico', 'nombre')
    preselecciones = {
        6: request.GET.get('sel6', ''),
        7: request.GET.get('sel7', ''),
        8: request.GET.get('sel8', ''),
        9: request.GET.get('sel9', ''),
    }

    def _redirigir_con_selecciones():
        query = urlencode({
            'sel6': preselecciones.get(6, '') or '',
            'sel7': preselecciones.get(7, '') or '',
            'sel8': preselecciones.get(8, '') or '',
            'sel9': preselecciones.get(9, '') or '',
        })
        return redirect(f'{reverse("activos:gestionar_taxonomia_iso")}?{query}')

    if request.method == 'POST':
        for nivel in (6, 7, 8, 9):
            preselecciones[nivel] = request.POST.get(f'seleccion_nivel{nivel}', '') or preselecciones[nivel]

        accion = (request.POST.get('accion') or 'crear').lower()
        clase_id = request.POST.get('clase_id')
        try:
            nivel_taxonomico = int(request.POST.get('nivel_taxonomico', 0))
        except ValueError:
            nivel_taxonomico = 0

        codigo = (request.POST.get('codigo') or '').strip().upper()
        nombre = (request.POST.get('nombre') or '').strip()
        descripcion = (request.POST.get('descripcion') or '').strip()
        padre_id = request.POST.get('padre_id') or None

        if accion == 'eliminar':
            if not clase_id:
                messages.error(request, 'No se especificó la opción a eliminar.')
                return _redirigir_con_selecciones()

            clase = get_object_or_404(ClaseEquipoISO14224, id=clase_id)
            tiene_hijos = ClaseEquipoISO14224.objects.filter(padre=clase).exists()
            if tiene_hijos:
                messages.error(request, 'No puedes eliminar esta opción porque tiene subniveles asociados.')
                return _redirigir_con_selecciones()

            nivel_taxonomico = clase.nivel_taxonomico
            clase.delete()
            preselecciones[nivel_taxonomico] = ''
            for inferior in (nivel_taxonomico + 1, nivel_taxonomico + 2, nivel_taxonomico + 3):
                if inferior in preselecciones:
                    preselecciones[inferior] = ''

            messages.success(request, 'Opción eliminada correctamente.')
            return _redirigir_con_selecciones()

        if nivel_taxonomico not in (6, 7, 8, 9):
            messages.error(request, 'Selecciona un nivel válido entre 6 y 9.')
            return _redirigir_con_selecciones()

        if not nombre:
            messages.error(request, 'Debes ingresar el nombre de la opción que quieres registrar o actualizar.')
            return _redirigir_con_selecciones()

        if not codigo:
            codigo_generado = slugify(nombre).upper().replace('-', '')
            codigo = codigo_generado[:50] or f'ISO{nivel_taxonomico}'

        padre = None
        if nivel_taxonomico > 6:
            if not padre_id:
                messages.error(request, f'Debes seleccionar primero el nivel {nivel_taxonomico - 1} antes de registrar o actualizar el nivel {nivel_taxonomico}.')
                return _redirigir_con_selecciones()

            padre = get_object_or_404(ClaseEquipoISO14224, id=padre_id)
            if padre.nivel_taxonomico != nivel_taxonomico - 1:
                messages.error(request, f'El padre seleccionado debe ser de nivel {nivel_taxonomico - 1}.')
                return _redirigir_con_selecciones()

        descripcion = descripcion or nombre

        # Validar unicidad de código
        existente = ClaseEquipoISO14224.objects.filter(codigo=codigo)
        if clase_id:
            existente = existente.exclude(id=clase_id)
        existente = existente.first()
        if existente:
            messages.warning(
                request,
                f'El código {codigo} ya existe como "{existente.nombre}". Usa otro código para registrar/actualizar.',
            )
            preselecciones[existente.nivel_taxonomico] = str(existente.id)
            return _redirigir_con_selecciones()

        if accion == 'actualizar':
            clase = get_object_or_404(ClaseEquipoISO14224, id=clase_id)
            if clase.nivel_taxonomico != nivel_taxonomico:
                messages.error(request, 'No se puede cambiar el nivel taxonómico de una opción existente.')
                return _redirigir_con_selecciones()

            clase.codigo = codigo
            clase.nombre = nombre
            clase.descripcion = descripcion
            clase.padre = padre
            clase.save()
            mensajes_accion = 'actualizada'
            clase_guardada = clase
        else:
            try:
                clase_guardada = ClaseEquipoISO14224.objects.create(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    nivel_taxonomico=nivel_taxonomico,
                    padre=padre,
                )
            except IntegrityError:
                messages.error(request, 'No se pudo guardar la opción. Verifica que el código sea único y vuelve a intentarlo.')
                return _redirigir_con_selecciones()
            mensajes_accion = 'registrada'

         # Mantén la ruta superior para facilitar cargas en serie.
        # Al crear, reinicia el nivel actual si es 7, 8 o 9 para poder
        # registrar varios hermanos seguidos sin tocar el padre.
        if accion == 'actualizar':
            preselecciones[nivel_taxonomico] = str(clase_guardada.id)
        else:
            if nivel_taxonomico == 6:
                preselecciones[nivel_taxonomico] = str(clase_guardada.id)
            else:
                preselecciones[nivel_taxonomico] = ''

        for inferior in (nivel_taxonomico + 1, nivel_taxonomico + 2, nivel_taxonomico + 3):
            if inferior in preselecciones:
                preselecciones[inferior] = ''

        mensaje_extra = ''
        if accion == 'crear' and nivel_taxonomico >= 8:
            mensaje_extra = ' El nivel actual quedó limpio para que puedas registrar otra opción con el mismo padre.'

        messages.success(
            request,
            f'Opción {mensajes_accion} en el nivel {nivel_taxonomico}. Puedes seguir agregando o editar niveles independientes sin completar hasta el nivel 9.{mensaje_extra}',
        )
        return _redirigir_con_selecciones()

    totales_por_nivel = {
        6: clases_qs.filter(nivel_taxonomico=6).count(),
        7: clases_qs.filter(nivel_taxonomico=7).count(),
        8: clases_qs.filter(nivel_taxonomico=8).count(),
        9: clases_qs.filter(nivel_taxonomico=9).count(),
    }

    contexto = {
        'organizacion': organizacion,
        'clases_iso_json': json.dumps(list(clases_qs.values(
            'id', 'codigo', 'nombre', 'descripcion', 'nivel_taxonomico', 'padre_id'
        )), ensure_ascii=False),
        'totales_por_nivel': totales_por_nivel,
        'preselecciones': preselecciones,
        'preselecciones_json': json.dumps(preselecciones, ensure_ascii=False),
    }
    return render(request, 'activos/gestionar_taxonomia_iso.html', contexto)

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

    ruta_jerarquica = []
    actual = activo
    while actual:
        ruta_jerarquica.insert(0, actual)
        actual = actual.parent

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
        'ruta_jerarquica': ruta_jerarquica,
    })

def dashboard_activos(request):
    """Dashboard principal de activos"""
    # Obtener organización del usuario (ajustar según tu modelo de usuario)
    # Por ahora asumimos que hay una organización
    try:
        organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    except Organizacion.DoesNotExist:
        return redirect('activos:crear_organizacion')
    
    # Solo considerar activos en el nivel de equipo (nivel 5 equivalente)
    filtro_nivel_equipo = Q(nivel_jerarquia__es_nivel_equipo=True) | Q(
        nivel_jerarquia__corresponde_iso_14224=5
    ) | Q(nivel_jerarquia__numero_nivel=5)
    activos_equipo = NodoActivo.objects.filter(organizacion=organizacion).filter(
        filtro_nivel_equipo
    )

    # Estadísticas
    total_activos = activos_equipo.count()
    activos_activos = activos_equipo.filter(estado='activo').count()
    activos_criticos = activos_equipo.filter(criticidad='alta').count()
    activos_mantenimiento = activos_equipo.filter(estado='mantenimiento').count()
    activos_fuera_servicio = activos_equipo.filter(estado='fuera_servicio').count()

    # Activos por nivel
    activos_por_nivel_raw = (
        activos_equipo
        .values("nivel_jerarquia__nombre_nivel")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    # Distribuciones para análisis rápido
    activos_por_estado_raw = (
        activos_equipo
        .values("estado")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    activos_por_criticidad_raw = (
        activos_equipo
        .values("criticidad")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    top_familias_raw = activos_equipo.filter(
        familia__isnull=False,
    ).values('familia__nombre').annotate(total=Count('id')).order_by('-total')[:5]
    estado_labels = dict(NodoActivo.ESTADOS)
    criticidad_labels = dict(NodoActivo.CRITICIDADES)
    activos_recientes = activos_equipo.select_related('familia', 'nivel_jerarquia').order_by('-creado_el')[:5]
    activos_recientes_info = [
        {
            'nombre': activo.nombre,
            'nivel': activo.nivel_jerarquia.nombre_nivel,
            'familia': activo.familia.nombre if activo.familia else 'Sin familia',
            'estado_label': estado_labels.get(activo.estado, activo.estado),
        }
        for activo in activos_recientes
    ]
    top_familias = [
        {
            'nombre': item['familia__nombre'] or 'Sin familia',
            'total': item['total'],
            'porcentaje': round((item['total'] / total_activos) * 100, 1) if total_activos else 0,
        }
        for item in top_familias_raw
    ]
    
    context = {
        'organizacion': organizacion,
        'total_activos': total_activos,
        'activos_activos': activos_activos,
        'activos_criticos': activos_criticos,
        'activos_por_nivel': [
            {
                'nivel': item['nivel_jerarquia__nombre_nivel'] or 'Sin nivel',
                'total': item['total'],
            }
            for item in activos_por_nivel_raw
            if item['total'] > 0
        ],
        'activos_por_estado': [
            {
                'estado': item['estado'],
                'label': estado_labels.get(item['estado'], 'Sin estado'),
                'total': item['total'],
                'porcentaje': round((item['total'] / total_activos) * 100, 1) if total_activos else 0,
            }
            for item in activos_por_estado_raw
            if item['total'] > 0
        ],
        'activos_por_criticidad': [
            {
                'criticidad': item['criticidad'],
                'label': criticidad_labels.get(item['criticidad'], 'Sin criticidad'),
                'total': item['total'],
                'porcentaje': round((item['total'] / total_activos) * 100, 1) if total_activos else 0,
            }
            for item in activos_por_criticidad_raw
            if item['total'] > 0
        ],
        'top_familias': top_familias,
        'activos_recientes': activos_recientes_info,
        'activos_mantenimiento': activos_mantenimiento,
        'activos_fuera_servicio': activos_fuera_servicio,
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
def niveles_jerarquia_datos(request):
    """Devuelve la lista de niveles de jerarquía en formato JSON para refrescar la vista."""
    organizacion = Organizacion.objects.first()
    niveles = NivelJerarquia.objects.filter(organizacion=organizacion).order_by('numero_nivel') if organizacion else []

    data = [
        {
            'numero_nivel': nivel.numero_nivel,
            'nombre_nivel': nivel.nombre_nivel,
            'corresponde_iso_14224': nivel.corresponde_iso_14224,
            'es_nivel_equipo': nivel.es_nivel_equipo,
            'requiere_tag': nivel.requiere_tag,
            'prefijo_tag': nivel.prefijo_tag,
            'formato_tag': nivel.formato_tag,
        }
        for nivel in niveles
    ]

    return JsonResponse({'niveles': data})


@login_required
def niveles_jerarquia_datos(request):
    """Devuelve la lista de niveles de jerarquía en formato JSON para refrescar la vista."""
    organizacion = Organizacion.objects.first()
    niveles = NivelJerarquia.objects.filter(organizacion=organizacion).order_by('numero_nivel') if organizacion else []

    data = [
        {
            'numero_nivel': nivel.numero_nivel,
            'nombre_nivel': nivel.nombre_nivel,
            'corresponde_iso_14224': nivel.corresponde_iso_14224,
            'es_nivel_equipo': nivel.es_nivel_equipo,
            'requiere_tag': nivel.requiere_tag,
            'prefijo_tag': nivel.prefijo_tag,
            'formato_tag': nivel.formato_tag,
        }
        for nivel in niveles
    ]

    return JsonResponse({'niveles': data})



@login_required
def vista_arbol_activos(request):
    """Vista del árbol interactivo de activos"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica
    
    # Obtener filtros
    nivel_id = (request.GET.get('nivel') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    busqueda = (request.GET.get('q') or '').strip()
    
    # Query base
    activos = (
        NodoActivo.objects.filter(organizacion=organizacion)
        .select_related('nivel_jerarquia', 'parent')
        .with_tree_fields()
    )

    # Aplicar filtros
    if nivel_id:
        activos = activos.filter(nivel_jerarquia_id=nivel_id)
    if estado:
        activos = activos.filter(estado=estado)
    if busqueda:
        terminos = [t for t in busqueda.split() if t]
        for termino in terminos:
            activos = activos.filter(
                Q(nombre__icontains=termino) |
                Q(codigo__icontains=termino) |
                Q(tag__icontains=termino)
            )

    activos = activos.order_by('id')
    activos_list = list(activos)
    total_filtrados = len(activos_list)

    # Niveles para filtro
    niveles = NivelJerarquia.objects.filter(organizacion=organizacion)
    
    filtros_activos = any([busqueda, nivel_id, estado])
    arbol_por_raiz = []
    ids_filtrados = {activo.id for activo in activos_list}

    if filtros_activos and activos_list:
        todos_activos = list(
            NodoActivo.objects.filter(organizacion=organizacion)
            .select_related('nivel_jerarquia', 'parent')
        )

        nodo_por_id = {nodo.id: nodo for nodo in todos_activos}
        hijos_por_padre = defaultdict(list)
        for nodo in todos_activos:
            hijos_por_padre[nodo.parent_id].append(nodo)

        for hijos in hijos_por_padre.values():
            hijos.sort(key=lambda x: (x.nivel_jerarquia.numero_nivel, x.nombre.lower()))

        def obtener_raiz(nodo):
            actual = nodo
            while actual and actual.parent_id:
                actual = nodo_por_id.get(actual.parent_id)
            return actual

        raices_en_orden = []
        raices_vistas = set()
        for nodo in activos_list:
            raiz = obtener_raiz(nodo)
            if raiz and raiz.id not in raices_vistas:
                raices_vistas.add(raiz.id)
                raices_en_orden.append(raiz)

        for raiz in raices_en_orden:
            filas = []

            def recorrer(nodo, profundidad=0):
                filas.append({'nodo': nodo, 'profundidad': profundidad})
                for hijo in hijos_por_padre.get(nodo.id, []):
                    recorrer(hijo, profundidad + 1)

            recorrer(raiz)
            niveles_presentes = sorted(
                {fila['nodo'].nivel_jerarquia.nombre_nivel for fila in filas}
            )
            arbol_por_raiz.append(
                {
                    'raiz': raiz,
                    'filas': filas,
                    'componentes': max(len(filas) - 1, 0),
                    'niveles_presentes': niveles_presentes,
                }
            )

    context = {
        'organizacion': organizacion,
        'activos': activos_list,
        'niveles': niveles,
        'nivel_seleccionado': nivel_id,
        'estado_seleccionado': estado,
        'busqueda': busqueda,
        'total_filtrados': total_filtrados,
        'filtros_activos': filtros_activos,
        'arbol_por_raiz': arbol_por_raiz,
        'ids_filtrados': ids_filtrados,
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

    def construir_contexto(nivel_preseleccionado=None, familia_seleccionada=None, valores_formulario=None):
        valores_serializables = valores_formulario
        if isinstance(valores_formulario, QueryDict):
            valores_serializables = valores_formulario.dict()

        niveles_qs = NivelJerarquia.objects.filter(organizacion=organizacion).order_by('numero_nivel')

        plantillas_qs = PlantillaActivo.objects.filter(
            organizacion=organizacion,
            es_activa=True,
        ).select_related('nivel_jerarquia')

        if padre:
            siguiente_nivel = padre.nivel_jerarquia.numero_nivel + 1
            niveles_qs = niveles_qs.filter(numero_nivel=siguiente_nivel)
            plantillas_qs = plantillas_qs.filter(
                nivel_jerarquia__numero_nivel=siguiente_nivel
            )

        niveles = list(niveles_qs)
        preseleccion = nivel_preseleccionado
        if preseleccion is None and padre and len(niveles) == 1:
            preseleccion = niveles[0].id

        familias = FamiliaActivo.objects.filter(
            Q(organizacion=organizacion) | Q(organizacion__isnull=True)
        ).order_by('nombre')

        plantillas_data = [
            {
                'id': p.id,
                'nombre': p.nombre,
                'nivel_id': p.nivel_jerarquia_id,
                'datos': p.datos_predeterminados,
            }
            for p in plantillas_qs
        ]

        clases_iso = ClaseEquipoISO14224.objects.all().values(
            'id', 'codigo', 'nombre', 'nivel_taxonomico', 'padre_id'
        ).order_by('nivel_taxonomico', 'nombre')

        return {
            'padre': padre,
            'niveles': niveles,
            'organizacion': organizacion,
            'familias': familias,
            'plantillas': plantillas_data,
            'plantillas_json': json.dumps(plantillas_data, ensure_ascii=False),
            'clases_iso_json': json.dumps(list(clases_iso), ensure_ascii=False),
            'nivel_preseleccionado': preseleccion,
            'familia_seleccionada': familia_seleccionada,
            'valores_formulario': valores_serializables or {},
        }

    if request.method == 'POST':
        # Procesar formulario
        nivel_id = request.POST.get('nivel_jerarquia')
        if not nivel_id:
            messages.error(request, 'Debes seleccionar un nivel de jerarquía para el activo.')
            context = construir_contexto(
                nivel_preseleccionado=None,
                familia_seleccionada=request.POST.get('familia'),
                valores_formulario=request.POST,
            )
            return render(request, 'activos/crear_activo.html', context)

        nivel = get_object_or_404(NivelJerarquia, id=nivel_id, organizacion=organizacion)

        if padre:
            siguiente_nivel = padre.nivel_jerarquia.numero_nivel + 1
            if nivel.numero_nivel != siguiente_nivel:
                messages.error(
                    request,
                    f'Debe seleccionar el nivel inmediato hijo ({siguiente_nivel}) respecto al activo padre.',
                )
                context = construir_contexto(
                    nivel_preseleccionado=nivel_id,
                    familia_seleccionada=request.POST.get('familia'),
                    valores_formulario=request.POST,
                )
                return render(request, 'activos/crear_activo.html', context)

        familia = None
        familia_id = request.POST.get('familia')
        if familia_id:
            familia = get_object_or_404(
                FamiliaActivo.objects.filter(
                    Q(organizacion=organizacion) | Q(organizacion__isnull=True)
                ),
                id=familia_id,
            )

        clase_iso_seleccionada = None
        clase_iso_texto = ''
        ruta_taxonomia_iso = []
        if nivel.numero_nivel >= 6:
            def obtener_o_crear_clase_iso(nivel_iso, padre_clase):
                existente_id = request.POST.get(f'iso_nivel{nivel_iso}_id')
                nuevo_nombre = (request.POST.get(f'iso_nivel{nivel_iso}_nuevo_nombre') or '').strip()
                nuevo_codigo = (request.POST.get(f'iso_nivel{nivel_iso}_nuevo_codigo') or '').strip()

                if existente_id:
                    return get_object_or_404(ClaseEquipoISO14224, id=existente_id)

                if nuevo_nombre:
                    if nivel_iso > 6 and not padre_clase:
                        messages.warning(
                            request,
                            f'Debes seleccionar o crear primero el nivel {nivel_iso - 1} antes de registrar el nivel {nivel_iso}.',
                        )
                        return None

                    codigo_generado = slugify(nuevo_nombre).upper().replace('-', '')
                    if not codigo_generado:
                        codigo_generado = f"ISO{nivel_iso}"
                    codigo_generado = codigo_generado[:20]
                    clase, creado = ClaseEquipoISO14224.objects.get_or_create(
                        codigo=nuevo_codigo or codigo_generado,
                        defaults={
                            'nombre': nuevo_nombre,
                            'descripcion': nuevo_nombre,
                            'nivel_taxonomico': nivel_iso,
                            'padre': padre_clase,
                        },
                    )

                    if not creado:
                        # Ajusta datos clave si ya existía pero con atributos diferentes
                        clase.nombre = clase.nombre or nuevo_nombre
                        clase.descripcion = clase.descripcion or nuevo_nombre
                        clase.nivel_taxonomico = nivel_iso
                        if padre_clase and clase.padre_id != padre_clase.id:
                            clase.padre = padre_clase
                        clase.save()

                    return clase

                return None

            padre_clase_iso = None

            for numero_nivel in range(6, 10):
                clase_iso = obtener_o_crear_clase_iso(numero_nivel, padre_clase_iso)
                if clase_iso:
                    padre_clase_iso = clase_iso
                    clase_iso_seleccionada = clase_iso
                    ruta_taxonomia_iso.append({
                        'id': clase_iso.id,
                        'codigo': clase_iso.codigo,
                        'nombre': clase_iso.nombre,
                        'nivel': clase_iso.nivel_taxonomico,
                        'padre_id': clase_iso.padre_id,
                    })

            if nivel.numero_nivel >= 6 and not clase_iso_seleccionada:
                messages.error(
                    request,
                    'Para los niveles 6 en adelante debes seleccionar o crear una ruta de taxonomía ISO 14224.',
                )
                context = construir_contexto(
                    nivel_preseleccionado=nivel_id,
                    familia_seleccionada=familia_id,
                    valores_formulario=request.POST,
                )
                return render(request, 'activos/crear_activo.html', context)

            if clase_iso_seleccionada:
                clase_iso_texto = f"{clase_iso_seleccionada.codigo} - {clase_iso_seleccionada.nombre}"
                clase_iso_texto = clase_iso_texto[:100]

        datos_personalizados = {}
        if ruta_taxonomia_iso:
            datos_personalizados['taxonomia_iso'] = ruta_taxonomia_iso
            datos_personalizados['taxonomia_iso_resumen'] = " / ".join(
                f"{nodo['codigo']} - {nodo['nombre']}" for nodo in ruta_taxonomia_iso
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
            clase_equipo_iso=clase_iso_texto,
            datos_personalizados=datos_personalizados,
            creado_por=request.user
        )

        messages.success(request, f'Activo "{activo.nombre}" creado exitosamente')
        return redirect('activos:detalle_activo', activo_id=activo.id)
    context = construir_contexto()
    return render(request, 'activos/crear_activo.html', context)
@login_required
def gestionar_plantillas(request):
    """Crear y consultar plantillas reutilizables para agilizar carga de activos."""
    organizacion = Organizacion.objects.first()

    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de gestionar plantillas.')
        return redirect('activos:dashboard_activos')

    niveles = NivelJerarquia.objects.filter(organizacion=organizacion).order_by('numero_nivel')
    clases_iso = ClaseEquipoISO14224.objects.all()
    plantillas = PlantillaActivo.objects.filter(
        organizacion=organizacion
    ).select_related('nivel_jerarquia', 'clase_equipo_iso').order_by('-creado_el')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        nivel_id = request.POST.get('nivel_jerarquia')
        clase_id = request.POST.get('clase_equipo_iso')
        datos_raw = request.POST.get('datos_predeterminados', '')
        es_activa = request.POST.get('es_activa') == 'on'

        if not nombre or not nivel_id:
            messages.error(request, 'Debe indicar un nombre y el nivel al que aplica la plantilla.')
            return redirect('activos:gestionar_plantillas')

        try:
            datos = json.loads(datos_raw) if datos_raw.strip() else {}
        except json.JSONDecodeError:
            messages.error(request, 'Los datos predeterminados deben tener un formato JSON válido.')
            return redirect('activos:gestionar_plantillas')

        nivel = get_object_or_404(NivelJerarquia, id=nivel_id, organizacion=organizacion)
        clase_iso = None
        if clase_id:
            clase_iso = get_object_or_404(ClaseEquipoISO14224, id=clase_id)

        PlantillaActivo.objects.create(
            nombre=nombre,
            organizacion=organizacion,
            nivel_jerarquia=nivel,
            clase_equipo_iso=clase_iso,
            datos_predeterminados=datos,
            es_activa=es_activa,
        )

        messages.success(request, 'Plantilla creada y disponible para su uso en la creación de activos.')
        return redirect('activos:gestionar_plantillas')

    contexto = {
        'organizacion': organizacion,
        'niveles': niveles,
        'clases_iso': clases_iso,
        'plantillas': plantillas,
        'ejemplo_datos': json.dumps({
            'nombre': 'Sistema de Inyección',
            'codigo': 'INJ-01',
            'descripcion': 'Subsistema predeterminado del molde',
            'estado': 'activo',
            'criticidad': 'media',
        }, indent=4),
    }

    return render(request, 'activos/gestionar_plantillas.html', contexto)


@login_required
def detalle_activo(request, activo_id):
    """Detalle de un activo"""
    organizacion = Organizacion.objects.first()  # Ajustar según tu lógica

    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de consultar activos.')
        return redirect('activos:dashboard_activos')

    activo = get_object_or_404(
        NodoActivo,
        id=activo_id,
        organizacion=organizacion
    )

    ruta_jerarquica = []
    actual = activo
    while actual:
        ruta_jerarquica.insert(0, actual)
        actual = actual.parent

    # Obtener hijos
    hijos = activo.children.select_related('nivel_jerarquia').all()
    hijos_count = hijos.count()

    # Obtener documentos y dependencias
    documentos = activo.documentos.select_related('subido_por').all()
    documentos_count = documentos.count()
    dependencias = activo.dependencias.order_by('nombre')
    dependencias_count = dependencias.count()

    criticidad_badges = {
        'alta': ('Alta', 'danger'),
        'media': ('Media', 'warning'),
        'baja': ('Baja', 'success'),
    }

    estado_badges = {
        'activo': ('Activo', 'success'),
        'mantenimiento': ('En Mantenimiento', 'warning'),
    }

    criticidad_label, criticidad_badge = criticidad_badges.get(
        activo.criticidad,
        ('No especificada', None),
    )

    estado_label, estado_badge = estado_badges.get(
        activo.estado,
        (activo.get_estado_display(), 'danger'),
    )

    datos_personalizados = activo.datos_personalizados if isinstance(activo.datos_personalizados, dict) else {}
    ruta_taxonomia_iso = datos_personalizados.get('taxonomia_iso', [])
    if not isinstance(ruta_taxonomia_iso, list):
        ruta_taxonomia_iso = []
    ruta_taxonomia_iso = sorted(ruta_taxonomia_iso, key=lambda nodo: nodo.get('nivel', 0))
    taxonomia_iso_resumen = datos_personalizados.get('taxonomia_iso_resumen', '')

    context = {
        'activo': activo,
        'hijos': hijos,
        'documentos': documentos,
        'dependencias': dependencias,
        'has_dependencias': dependencias_count > 0,
        'has_hijos': hijos_count > 0,
        'has_documentos': documentos_count > 0,
        'documentos_count': documentos_count,
        'hijos_count': hijos_count,
        'dependencias_count': dependencias_count,
        'criticidad_label': criticidad_label,
        'criticidad_badge': criticidad_badge,
        'estado_label': estado_label,
        'estado_badge': estado_badge,
        'ruta_jerarquica': ruta_jerarquica,
        'padre_activo': activo.parent,
        'nivel_iso': activo.nivel_jerarquia.corresponde_iso_14224,
        'ruta_taxonomia_iso': ruta_taxonomia_iso,
        'taxonomia_iso_resumen': taxonomia_iso_resumen,
    }

    return render(request, 'activos/detalle_activo.html', context)

@login_required
def hoja_vida_equipo(request):
    """Consulta del histórico de novedades y OT por equipo."""
    organizacion = Organizacion.objects.first()
    if not organizacion:
        messages.error(request, "Debe configurar una organización antes de consultar equipos.")
        return redirect("activos:dashboard_activos")

    equipo_id = request.GET.get("equipo") or ""
    termino_busqueda = request.GET.get("q", "").strip()
    exportar = request.GET.get("export") == "1"
    filtro_nivel_equipo = Q(nivel_jerarquia__es_nivel_equipo=True) | Q(
        nivel_jerarquia__corresponde_iso_14224=5
    ) | Q(nivel_jerarquia__numero_nivel=5)
    equipos_qs = NodoActivo.objects.filter(organizacion=organizacion).filter(
        filtro_nivel_equipo
    )
    equipos_sugeridos = None
    if termino_busqueda and not equipo_id:
        equipos_qs = equipos_qs.filter(
            Q(nombre__icontains=termino_busqueda)
            | Q(tag__icontains=termino_busqueda)
            | Q(codigo__icontains=termino_busqueda)
            | Q(descripcion__icontains=termino_busqueda)
        )
        equipos_sugeridos = equipos_qs
        equipo_exacto = equipos_qs.filter(
            Q(nombre__iexact=termino_busqueda)
            | Q(tag__iexact=termino_busqueda)
            | Q(codigo__iexact=termino_busqueda)
        ).first()
        if equipo_exacto:
            equipo_id = str(equipo_exacto.id)
        elif equipos_qs.count() == 1:
            equipo_id = str(equipos_qs.first().id)
    equipos = equipos_qs.order_by("nombre")

    equipo = None
    novedades = []
    ordenes = []
    documentos = []
    if equipo_id:
        equipo = get_object_or_404(
            NodoActivo, id=equipo_id, organizacion=organizacion
        )
        termino_equipo = ""
        if termino_busqueda:
            termino_equipo = termino_busqueda.lower()
        novedades = (
            Novedad.objects.filter(equipo=equipo)
            .select_related("actividad")
            .prefetch_related("ordenes_trabajo")
            .order_by("-fecha", "-id")
        )
        ordenes = (
            WorkOrder.objects.filter(equipo=equipo)
            .select_related("responsable", "actividad", "novedad_origen")
            .order_by("-fecha_creacion")
        )
        documentos = DocumentoActivo.objects.filter(activo=equipo).order_by("-subido_el")
        if termino_busqueda and (
            not equipo
            or termino_equipo
            not in (
                (equipo.nombre or "").lower(),
                (equipo.tag or "").lower(),
                (equipo.codigo or "").lower(),
                (equipo.descripcion or "").lower(),
            )
        ):
            novedades = novedades.filter(
                Q(actividad__nombre__icontains=termino_busqueda)
                | Q(descripcion__icontains=termino_busqueda)
                | Q(estado__icontains=termino_busqueda)
            )
            ordenes = ordenes.filter(
                Q(titulo__icontains=termino_busqueda)
                | Q(descripcion__icontains=termino_busqueda)
                | Q(estado__icontains=termino_busqueda)
                | Q(responsable__nombre__icontains=termino_busqueda)
                | Q(responsable__user__first_name__icontains=termino_busqueda)
                | Q(responsable__user__last_name__icontains=termino_busqueda)
                | Q(responsable__user__username__icontains=termino_busqueda)
            )
            documentos = documentos.filter(
                Q(nombre__icontains=termino_busqueda)
                | Q(descripcion__icontains=termino_busqueda)
                | Q(tipo_documento__icontains=termino_busqueda)
            )
            termino_upper = termino_busqueda.upper()
            if termino_upper.startswith("OT-"):
                termino_upper = termino_upper[3:]
            if termino_upper.isdigit():
                ordenes = ordenes.filter(consecutivo=int(termino_upper))

        if exportar:
            import csv
            from django.utils import timezone

            response = HttpResponse(content_type="text/csv")
            fecha_exportacion = timezone.localdate().strftime("%Y%m%d")
            response[
                "Content-Disposition"
            ] = f'attachment; filename="hoja_vida_{equipo.codigo}_{fecha_exportacion}.csv"'
            writer = csv.writer(response)
            writer.writerow(
                [
                    "Tipo",
                    "Fecha",
                    "Código",
                    "Título/Nombre",
                    "Estado",
                    "Prioridad",
                    "Responsable",
                    "Actividad/Tipo",
                    "Descripción",
                    "Enlace",
                ]
            )
            for novedad in novedades:
                writer.writerow(
                    [
                        "Novedad",
                        novedad.fecha.strftime("%Y-%m-%d"),
                        "",
                        novedad.actividad.nombre if novedad.actividad else "Sin actividad",
                        novedad.get_estado_display(),
                        "",
                        "",
                        "",
                        novedad.descripcion or "",
                        "",
                    ]
                )
            for orden in ordenes:
                responsable = orden.responsable.nombre_display if orden.responsable else ""
                writer.writerow(
                    [
                        "OT",
                        orden.fecha_creacion.strftime("%Y-%m-%d"),
                        orden.codigo,
                        orden.titulo,
                        orden.get_estado_display(),
                        orden.get_prioridad_display(),
                        responsable,
                        orden.actividad.nombre if orden.actividad else "",
                        orden.descripcion or "",
                        "",
                    ]
                )
            for doc in documentos:
                writer.writerow(
                    [
                        "Documento",
                        doc.subido_el.strftime("%Y-%m-%d"),
                        "",
                        doc.nombre,
                        "",
                        "",
                        doc.subido_por.get_full_name()
                        if doc.subido_por_id and doc.subido_por.get_full_name()
                        else doc.subido_por.username
                        if doc.subido_por_id
                        else "",
                        doc.get_tipo_documento_display(),
                        doc.descripcion or "",
                        doc.archivo.url if doc.archivo else "",
                    ]
                )
            return response

    return render(
        request,
        "activos/hoja_vida_equipo.html",
        {
            "equipos": equipos,
            "equipo": equipo,
            "equipo_filtro": equipo_id,
            "termino_busqueda": termino_busqueda,
            "equipos_sugeridos": equipos_sugeridos,
            "novedades": novedades,
            "ordenes": ordenes,
            "documentos": documentos,
            "total_novedades": len(novedades),
            "total_ordenes": len(ordenes),
            "total_documentos": len(documentos),
        },
    )


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

    if not organizacion:
        messages.error(request, 'Debe configurar una organización antes de importar activos.')
        return redirect('activos:dashboard_activos')
    
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo_excel = request.FILES['archivo_excel']
        
        # Guardar archivo temporalmente
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in archivo_excel.chunks():
                tmp.write(chunk)
            ruta_temporal = tmp.name
        
        # Importar
        importador = ImportadorExcelActivos(organizacion, usuario=request.user)
        try:
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
        
        finally:
            if 'ruta_temporal' in locals() and os.path.exists(ruta_temporal):
                os.unlink(ruta_temporal)

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

    # Crear datos de ejemplo con jerarquía básica y campos clave
    datos_ejemplo = {
        'nivel': [1, 2, 3, 6, 7, 8, 9],
        'nombre': [
            'Industria Principal',
            'Línea de negocio',
            'Planta Norte',
            'Bomba Progresiva 01',
            'Tren Hidráulico',
            'Motor Principal',
            'Rodamiento LC',
        ],
        'codigo': ['IND-01', 'LN-01', 'PL-01', 'BP-01', 'SU-01', 'IM-01', 'PZ-01'],
        'padre': ['', 'IND-01', 'LN-01', 'PL-01', 'BP-01', 'SU-01', 'IM-01'],
        'familia': [
            'Infraestructura',
            'Infraestructura',
            'Infraestructura',
            'Equipos rotativos',
            'Subcomponentes',
            'Subcomponentes',
            'Subcomponentes',
        ],
        'descripcion': [
            'Industria de gestión de residuos',
            'Negocio de recolección y transporte',
            'Planta de tratamiento Norte',
            'Bomba progresiva de lodos',
            'Conjunto hidráulico',
            'Motor eléctrico 25 HP',
            'Rodamiento 6314 C3',
        ],
        'fabricante': ['', '', '', 'Seepex', '', 'WEG', 'SKF'],
        'modelo': ['', '', '', 'MD 012-24', '', 'W22', '6314 C3'],
        'serie': ['', '', '', 'BP1-2023', '', 'MOT-25HP', ''],
        'criticidad': ['', '', '', 'alta', 'media', 'media', 'media'],
        'datos_personalizados (JSON)': [
            '{"linea_base": "ISO 14224"}',
            '{"enfoque": "Industria"}',
            '{"turnos": "24/7"}',
            '{"flujo_m3h": 12, "rpm_operacion": 480}',
            '{"presion_diseno_bar": 8}',
            '{"eficiencia": "94%"}',
            '{"inventario_min": 2}',
        ],
    }

    # Hoja 1: plantilla de activos
    df_plantilla = pd.DataFrame(datos_ejemplo)

    # Hoja 2: guía rápida de campos
    df_campos = pd.DataFrame(
        [
            {
                'Campo': 'nivel',
                'Requerido': 'Sí',
                'Descripción': 'Número de nivel ISO 14224 (1-9) según la jerarquía configurada.',
                'Ejemplo': '6',
            },
            {
                'Campo': 'nombre',
                'Requerido': 'Sí',
                'Descripción': 'Nombre descriptivo del activo.',
                'Ejemplo': 'Bomba Progresiva 01',
            },
            {
                'Campo': 'codigo',
                'Requerido': 'Sí',
                'Descripción': 'Código único en el nivel. Se usará para crear el tag si aplica.',
                'Ejemplo': 'BP-01',
            },
            {
                'Campo': 'padre',
                'Requerido': 'Solo si nivel > 1',
                'Descripción': 'Código del activo padre ya listado en la hoja.',
                'Ejemplo': 'PL-01',
            },
            {
                'Campo': 'familia',
                'Requerido': 'Opcional',
                'Descripción': 'Nombre de la familia de activo para clasificar (debe existir).',
                'Ejemplo': 'Equipos rotativos',
            },
            {
                'Campo': 'descripcion',
                'Requerido': 'Opcional',
                'Descripción': 'Detalle del activo o su función.',
                'Ejemplo': 'Bomba progresiva de lodos',
            },
            {
                'Campo': 'fabricante/modelo/serie',
                'Requerido': 'Opcional',
                'Descripción': 'Datos de placa del activo si aplica.',
                'Ejemplo': 'Seepex / MD 012-24 / BP1-2023',
            },
            {
                'Campo': 'criticidad',
                'Requerido': 'Opcional',
                'Descripción': 'Valor libre (ej: alta, media, baja).',
                'Ejemplo': 'alta',
            },
            {
                'Campo': 'datos_personalizados (JSON)',
                'Requerido': 'Opcional',
                'Descripción': 'Campos adicionales en formato JSON válido.',
                'Ejemplo': '{"flujo_m3h": 12}',
            },
        ]
    )

    # Hoja 3: catálogos de referencia
    df_catalogos = pd.DataFrame(
        [
            {'Tipo': 'Nivel', 'Valor': '1', 'Detalle': 'Industria'},
            {'Tipo': 'Nivel', 'Valor': '2', 'Detalle': 'Negocio'},
            {'Tipo': 'Nivel', 'Valor': '3', 'Detalle': 'Instalación'},
            {'Tipo': 'Nivel', 'Valor': '4', 'Detalle': 'Planta/Unidad'},
            {'Tipo': 'Nivel', 'Valor': '5', 'Detalle': 'Sección/Sistema'},
            {'Tipo': 'Nivel', 'Valor': '6', 'Detalle': 'Equipo'},
            {'Tipo': 'Nivel', 'Valor': '7', 'Detalle': 'Subunidad'},
            {'Tipo': 'Nivel', 'Valor': '8', 'Detalle': 'Item mantenible'},
            {'Tipo': 'Nivel', 'Valor': '9', 'Detalle': 'Parte/Pieza'},
            {'Tipo': 'Familia', 'Valor': 'Infraestructura', 'Detalle': 'Estructuras, edificios y ubicaciones'},
            {'Tipo': 'Familia', 'Valor': 'Equipos rotativos', 'Detalle': 'Bombas, compresores y motores'},
            {'Tipo': 'Familia', 'Valor': 'Subcomponentes', 'Detalle': 'Conjuntos menores y partes'},
            {'Tipo': 'Familia', 'Valor': 'Sistema de aire', 'Detalle': 'Redes y equipos de aire comprimido'},
            {'Tipo': 'Familia', 'Valor': 'Sistema de bombeo', 'Detalle': 'Sistemas hidráulicos y de transferencia'},
        ]
    )

    # Guardar en archivo temporal con varias hojas
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        ruta_temporal = tmp.name

    with pd.ExcelWriter(ruta_temporal, engine='openpyxl') as writer:
        df_plantilla.to_excel(writer, sheet_name='Activos', index=False)
        df_campos.to_excel(writer, sheet_name='Instrucciones', index=False)
        df_catalogos.to_excel(writer, sheet_name='Catalogos', index=False)

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
