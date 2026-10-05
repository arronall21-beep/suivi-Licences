"""Matrice rôles → permissions. Toute autorisation est vérifiée côté backend (jamais seulement dans l'UI)."""

ROLE_LABELS = {
    "ADMIN": "Administrateur",
    "MANAGER": "Gestionnaire",
    "VIEWER": "Lecture seule",
}

ROLE_DESCRIPTIONS = {
    "ADMIN": "Accès complet : utilisateurs, paramètres, SMTP, journal d'audit, import, suppression, données métier.",
    "MANAGER": "Accès métier : création et modification des actifs, contrats, fournisseurs et affectations ; "
    "exports et notifications. Pas d'accès à l'administration, à l'import ni à la suppression.",
    "VIEWER": "Consultation : dashboard, actifs, contrats, planning, notifications et exports. Aucune modification.",
}

# Libellés lisibles des permissions (page Rôles)
PERMISSION_LABELS = {
    "data:read": "Consulter dashboard, actifs, contrats, planning, affectations",
    "data:write": "Créer et modifier actifs, contrats, fournisseurs, affectations (et désaffecter)",
    "data:delete": "Supprimer actifs, contrats, fournisseurs",
    "import:run": "Importer un fichier Excel",
    "export:run": "Exporter en Excel",
    "notifications:read": "Consulter ses notifications",
    "alerts:run": "Déclencher le contrôle des alertes",
    "admin:users": "Gérer les utilisateurs et les rôles",
    "admin:settings": "Modifier les paramètres généraux et les alertes",
    "admin:smtp": "Configurer et tester le SMTP",
    "admin:audit": "Consulter le journal d'audit",
    "admin:system": "Consulter l'état du système",
}

_READ = {"data:read", "export:run", "notifications:read"}
_ADMIN_ONLY = {
    "data:delete",
    "import:run",
    "alerts:run",
    "admin:users",
    "admin:settings",
    "admin:smtp",
    "admin:audit",
    "admin:system",
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "VIEWER": frozenset(_READ),
    "MANAGER": frozenset(_READ | {"data:write"}),
    "ADMIN": frozenset(_READ | {"data:write"} | _ADMIN_ONLY),
}


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for(role)
