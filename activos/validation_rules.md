# Reglas de validación backend (ISO 14224 + multi-tenant)

1. **Aislamiento por organización**  
   - Todos los modelos con organización (`NodoActivo`, `NivelJerarquia`, `FamiliaActivo`, `CatalogoParte`, `PlantillaActivo`, `PlantillaNodoISO`) deben filtrarse por usuario usando `TenantAwareManager.for_user(user)`.  
   - Ninguna instancia puede referenciar objetos de otra organización (padres, plantillas, partes).

2. **Integridad jerárquica ISO 14224**  
   - `NivelJerarquia.numero_nivel` está limitado a 1-9.  
   - Entre `NodoActivo.parent` y el hijo, el número de nivel debe avanzar exactamente en +1.  
   - Los nodos de nivel ISO 9 **deben** referenciar `CatalogoParte`; niveles distintos no pueden hacerlo.
   - `PlantillaNodoISO` exige que el `nivel_iso` esté en 1-9 y que el `parent` pertenezca a la misma plantilla.

3. **Unicidad y referencialidad**  
   - `FamiliaActivo`, `CatalogoParte` y `PlantillaNodoISO` definen unicidad por organización/plantilla para evitar duplicados.  
   - `NodoActivo` valida que `organizacion` coincida con la de su `parent` y con la de la parte asociada.

4. **Disponibilidad del catálogo**  
   - Solo se pueden sugerir/seleccionar partes con `es_activo=True`.  
   - El catálogo de nivel 9 se consulta restringido por organización.

5. **TAGs y códigos**  
   - Los TAGs continúan generándose solo en niveles que lo requieren; los códigos mantienen unicidad dentro de la organización.

Estas reglas deben ejecutarse mediante `full_clean()` antes de persistir objetos y deben replicarse en serializadores/API para cargas masivas.
