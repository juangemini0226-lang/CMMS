from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from activos.models import Organizacion, NivelJerarquia

class Command(BaseCommand):
    help = 'Crea datos iniciales para la aplicación activos (ISO 14224 - 9 niveles)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('╔═══════════════════════════════════════════════════════════╗'))
        self.stdout.write(self.style.SUCCESS('║    GESTIÓN DE ACTIVOS ESTRA - INICIALIZACIÓN DEL SISTEMA  ║'))
        self.stdout.write(self.style.SUCCESS('║    ISO 14224 Completo (9 Niveles)                         ║'))
        self.stdout.write(self.style.SUCCESS('╚═══════════════════════════════════════════════════════════╝'))
        self.stdout.write('')
        
        # 1. CREAR SUPERUSUARIO
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@estra.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('✓ Superusuario creado: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Superusuario "admin" ya existe'))
        
        admin_user = User.objects.get(username='admin')
        
        # 2. CREAR U OBTENER ORGANIZACIÓN
        org, org_created = Organizacion.objects.get_or_create(
            codigo='ESTRA',
            defaults={
                'nombre': 'Estra Soluciones',
                'descripcion': 'Empresa de manejo de residuos y soluciones integrales',
                'creado_por': admin_user
            }
        )
        
        if org_created:
            self.stdout.write(self.style.SUCCESS('✓ Organización creada: Estra Soluciones'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Organización "Estra" ya existe'))
        
        # 3. VERIFICAR SI YA EXISTEN NIVELES
        niveles_existentes = NivelJerarquia.objects.filter(organizacion=org).count()
        
        if niveles_existentes > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠ Ya existen {niveles_existentes} niveles para esta organización.'))
            respuesta = input('¿Deseas eliminarlos y recrearlos? (s/n): ')
            
            if respuesta.lower() != 's':
                self.stdout.write(self.style.ERROR(' Operación cancelada'))
                return
            
            NivelJerarquia.objects.filter(organizacion=org).delete()
            self.stdout.write(self.style.SUCCESS('✓ Niveles anteriores eliminados'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Creando jerarquía completa ISO 14224 (9 niveles)...'))
        self.stdout.write('')
        
        # 4. CREAR JERARQUÍA COMPLETA (9 NIVELES)
        niveles_config = [
            # NIVELES 1-5: BASADOS EN UBICACIÓN
            {
                'numero': 1, 
                'nombre': 'Industria', 
                'iso': 1, 
                'equipo': False, 
                'tag': False, 
                'prefijo': '', 
                'formato': '',
                'descripcion': 'Tipo de industria principal (Manejo de Residuos, Petróleo, Gas)'
            },
            {
                'numero': 2, 
                'nombre': 'Negocio', 
                'iso': 2, 
                'equipo': False, 
                'tag': False, 
                'prefijo': '', 
                'formato': '',
                'descripcion': 'Línea de negocio o flujo de proceso'
            },
            {
                'numero': 3, 
                'nombre': 'Instalación', 
                'iso': 3, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'I', 
                'formato': '{PREFIJO}-{CODIGO}',
                'descripcion': 'Categoría de instalación o centro de operaciones'
            },
            {
                'numero': 4, 
                'nombre': 'Planta/Unidad', 
                'iso': 4, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'P', 
                'formato': '{PADRE}-{PREFIJO}-{CODIGO}',
                'descripcion': 'Planta industrial o unidad de proceso'
            },
            {
                'numero': 5, 
                'nombre': 'Sección/Sistema', 
                'iso': 5, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'S', 
                'formato': '{PADRE}-{PREFIJO}-{CODIGO}',
                'descripcion': 'Sistema principal dentro de la planta'
            },
            
            # NIVEL 6: EQUIPO PRINCIPAL
            {
                'numero': 6, 
                'nombre': 'Equipo', 
                'iso': 6, 
                'equipo': True, 
                'tag': True, 
                'prefijo': 'EQ', 
                'formato': '{PADRE}-{PREFIJO}-{SECUENCIA}',
                'descripcion': ' NIVEL PRINCIPAL ISO 14224: Clase de equipo'
            },
            
            # NIVELES 7-9: SUBDIVISIÓN DE EQUIPO
            {
                'numero': 7, 
                'nombre': 'Subunidad', 
                'iso': 7, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'SU', 
                'formato': '{PADRE}-{PREFIJO}-{SECUENCIA}',
                'descripcion': 'Subsistema del equipo (lubricación, enfriamiento, control)'
            },
            {
                'numero': 8, 
                'nombre': 'Item Mantenible', 
                'iso': 8, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'IM', 
                'formato': '{PADRE}-{PREFIJO}-{SECUENCIA}',
                'descripcion': 'Elemento mantenible (Motor, Rodamientos, Sellos)'
            },
            {
                'numero': 9, 
                'nombre': 'Parte/Pieza', 
                'iso': 9, 
                'equipo': False, 
                'tag': True, 
                'prefijo': 'P', 
                'formato': '{PADRE}-{PREFIJO}-{SECUENCIA}',
                'descripcion': 'Pieza individual (Tornillos, Empaques, O-rings)'
            },
        ]
        
        # Crear niveles
        self.stdout.write(self.style.SUCCESS('┌─────────────────────────────────────────────────────────┐'))
        self.stdout.write(self.style.SUCCESS('│  NIVELES 1-5: Basados en UBICACIÓN                     │'))
        self.stdout.write(self.style.SUCCESS('└─────────────────────────────────────────────────────────┘'))
        
        for i, nivel_data in enumerate(niveles_config):
            NivelJerarquia.objects.create(
                organizacion=org,
                numero_nivel=nivel_data['numero'],
                nombre_nivel=nivel_data['nombre'],
                descripcion=nivel_data['descripcion'],
                corresponde_iso_14224=nivel_data['iso'],
                es_nivel_equipo=nivel_data['equipo'],
                requiere_tag=nivel_data['tag'],
                prefijo_tag=nivel_data['prefijo'],
                formato_tag=nivel_data['formato']
            )
            
            icon = '⭐' if nivel_data['equipo'] else '  '
            self.stdout.write(self.style.SUCCESS(
                f"{icon} Nivel {nivel_data['numero']}: {nivel_data['nombre']:<20} (ISO {nivel_data['iso']})"
            ))
            
            # Separadores
            if nivel_data['numero'] == 5:
                self.stdout.write(self.style.SUCCESS('┌─────────────────────────────────────────────────────────┐'))
                self.stdout.write(self.style.SUCCESS('│  ⭐ NIVEL 6: EQUIPO (Foco Principal)                   │'))
                self.stdout.write(self.style.SUCCESS('└─────────────────────────────────────────────────────────┘'))
            elif nivel_data['numero'] == 6:
                self.stdout.write(self.style.SUCCESS('┌─────────────────────────────────────────────────────────┐'))
                self.stdout.write(self.style.SUCCESS('│  NIVELES 7-9: SUBDIVISIÓN DE EQUIPO                    │'))
                self.stdout.write(self.style.SUCCESS('└─────────────────────────────────────────────────────────┘'))
        
        # Resumen final
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('╔═══════════════════════════════════════════════════════════╗'))
        self.stdout.write(self.style.SUCCESS('║            SISTEMA INICIALIZADO EXITOSAMENTE           ║'))
        self.stdout.write(self.style.SUCCESS('╚═══════════════════════════════════════════════════════════╝'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📌 Credenciales: admin / admin123'))
        self.stdout.write(self.style.SUCCESS('🌐 Admin: http://127.0.0.1:8000/admin/'))
        self.stdout.write(self.style.SUCCESS('📦 Activos: http://127.0.0.1:8000/activos/'))
        self.stdout.write('')
