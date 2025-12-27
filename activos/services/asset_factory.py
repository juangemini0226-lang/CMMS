from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from activos.models import CatalogoParte, NivelJerarquia, NodoActivo, Organizacion


class AssetInstantiationService:
    """Motor de instanciación para crear árboles ISO 14224 desde plantillas JSON."""

    def __init__(self, organization: Organizacion, user: User, dry_run: bool = False) -> None:
        self.organization = organization
        self.user = user
        self.dry_run = dry_run
        self.level_cache: Dict[int, NivelJerarquia] = {}
        self.created_nodes: List[NodoActivo] = []

    def create_asset_from_template(self, payload_json: Dict[str, Any]) -> List[NodoActivo]:
        """Crea un árbol de activos desde una plantilla JSON de manera transaccional."""
        roots = payload_json.get("nodos") or []
        if not roots:
            raise ValidationError("El JSON de plantilla no contiene nodos a instanciar.")

        # Validación previa de SKUs para evitar escrituras parciales.
        self._validate_skus(roots)

        if self.dry_run:
            return []

        with transaction.atomic():
            for node_data in roots:
                self._process_node(node_data, parent=None)
        return self.created_nodes

    def _process_node(self, node_data: Dict[str, Any], parent: Optional[NodoActivo]) -> NodoActivo:
        nivel_iso = node_data.get("nivel_iso")
        codigo = node_data.get("codigo")
        nombre = node_data.get("nombre")
        children = node_data.get("children", [])
        catalog_ref = node_data.get("catalogo_parte_ref") or node_data.get("catalog_ref_placeholder")

        if nivel_iso is None or codigo is None or nombre is None:
            raise ValidationError("Cada nodo requiere 'nivel_iso', 'codigo' y 'nombre'.")

        nivel_jerarquia = self._get_level_for_iso(nivel_iso)

        if NodoActivo.objects.filter(
            organizacion=self.organization, parent=parent, codigo=codigo
        ).exists():
            raise ValidationError(
                f"Ya existe un nodo con código '{codigo}' bajo el padre '{parent}'."
            )

        catalogo_parte = None
        if nivel_iso == 9:
            catalogo_parte = self._resolve_catalog_part(catalog_ref)

        nodo = NodoActivo(
            organizacion=self.organization,
            nivel_jerarquia=nivel_jerarquia,
            parent=parent,
            nombre=nombre,
            codigo=codigo,
            creado_por=self.user,
            catalogo_parte=catalogo_parte,
        )
        nodo.full_clean()
        nodo.save()
        self.created_nodes.append(nodo)

        for child in children:
            self._process_node(child, parent=nodo)
        return nodo

    def _get_level_for_iso(self, nivel_iso: int) -> NivelJerarquia:
        if nivel_iso in self.level_cache:
            return self.level_cache[nivel_iso]
        try:
            level = NivelJerarquia.objects.get(
                organizacion=self.organization, corresponde_iso_14224=nivel_iso
            )
        except NivelJerarquia.DoesNotExist as exc:
            raise ValidationError(
                f"No existe nivel de jerarquía configurado para ISO {nivel_iso} en esta organización."
            ) from exc
        self.level_cache[nivel_iso] = level
        return level

    def _resolve_catalog_part(self, sku: Optional[str]) -> Optional[CatalogoParte]:
        if not sku:
            raise ValidationError("Los nodos de nivel 9 requieren 'catalogo_parte_ref' o SKU definido.")
        try:
            part = CatalogoParte.objects.get(
                organizacion=self.organization, codigo_sku=sku, es_activo=True
            )
        except CatalogoParte.DoesNotExist as exc:
            raise ValidationError(
                f"El SKU '{sku}' requerido por la plantilla no existe en el catálogo de esta organización o está obsoleto."
            ) from exc
        return part

    def _validate_skus(self, roots: Iterable[Dict[str, Any]]) -> None:
        """Valida previamente que todos los SKUs referenciados existan y estén activos."""
        skus = self._collect_skus(roots)
        if not skus:
            return
        missing: List[str] = []
        inactive: List[str] = []
        parts = CatalogoParte.objects.filter(
            organizacion=self.organization, codigo_sku__in=skus
        )
        active_map = {p.codigo_sku: p.es_activo for p in parts}
        for sku in skus:
            if sku not in active_map:
                missing.append(sku)
            elif not active_map[sku]:
                inactive.append(sku)
        if missing or inactive:
            messages: List[str] = []
            if missing:
                messages.append(
                    "No existen en catálogo: " + ", ".join(sorted(set(missing)))
                )
            if inactive:
                messages.append(
                    "SKUs inactivos/obsoletos: " + ", ".join(sorted(set(inactive)))
                )
            raise ValidationError(" ; ".join(messages))

    def _collect_skus(self, nodes: Iterable[Dict[str, Any]]) -> List[str]:
        collected: List[str] = []
        for node in nodes:
            sku = node.get("catalogo_parte_ref") or node.get("catalog_ref_placeholder")
            if sku:
                collected.append(sku)
            children = node.get("children") or []
            collected.extend(self._collect_skus(children))
        return collected