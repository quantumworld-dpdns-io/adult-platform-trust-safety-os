"""Role-based access control (RBAC) with role and permission enums."""

from __future__ import annotations

from enum import Enum
from typing import Any


class Role(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    REVIEWER = "reviewer"
    USER = "user"


class Permission(str, Enum):
    # User management
    CREATE_USER = "user:create"
    READ_USER = "user:read"
    UPDATE_USER = "user:update"
    DELETE_USER = "user:delete"
    BAN_USER = "user:ban"
    IMPERSONATE_USER = "user:impersonate"

    # Content moderation
    VIEW_CONTENT = "content:view"
    APPROVE_CONTENT = "content:approve"
    REJECT_CONTENT = "content:reject"
    FLAG_CONTENT = "content:flag"
    DELETE_CONTENT = "content:delete"

    # Moderation queue
    VIEW_QUEUE = "queue:view"
    ASSIGN_QUEUE = "queue:assign"
    RESOLVE_QUEUE = "queue:resolve"

    # Analytics & reporting
    VIEW_ANALYTICS = "analytics:view"
    VIEW_REPORTS = "reports:view"
    GENERATE_REPORT = "reports:generate"

    # System administration
    MANAGE_ROLES = "system:manage_roles"
    MANAGE_SETTINGS = "system:settings"
    VIEW_AUDIT_LOG = "system:audit_log"
    MANAGE_API_KEYS = "system:api_keys"
    MANAGE_MFA = "system:mfa"

    # Delegation
    CREATE_DELEGATION = "delegation:create"
    VIEW_DELEGATION = "delegation:view"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.MODERATOR: {
        Permission.VIEW_CONTENT,
        Permission.APPROVE_CONTENT,
        Permission.REJECT_CONTENT,
        Permission.FLAG_CONTENT,
        Permission.VIEW_QUEUE,
        Permission.ASSIGN_QUEUE,
        Permission.RESOLVE_QUEUE,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_REPORTS,
        Permission.READ_USER,
        Permission.BAN_USER,
        Permission.CREATE_DELEGATION,
        Permission.VIEW_DELEGATION,
    },
    Role.REVIEWER: {
        Permission.VIEW_CONTENT,
        Permission.APPROVE_CONTENT,
        Permission.REJECT_CONTENT,
        Permission.VIEW_QUEUE,
        Permission.RESOLVE_QUEUE,
        Permission.VIEW_ANALYTICS,
        Permission.READ_USER,
    },
    Role.USER: {
        Permission.READ_USER,
    },
}


class RoleBasedAccessControl:
    def __init__(self) -> None:
        self._user_roles: dict[str, set[Role]] = {}

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        roles = self._user_roles.get(user_id, set())
        for role in roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                return True
        return False

    def assign_role(self, user_id: str, role: Role) -> None:
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role)

    def revoke_role(self, user_id: str, role: Role) -> bool:
        roles = self._user_roles.get(user_id)
        if roles and role in roles:
            roles.discard(role)
            if not roles:
                del self._user_roles[user_id]
            return True
        return False

    def get_user_roles(self, user_id: str) -> list[Role]:
        return sorted(self._user_roles.get(user_id, set()))

    def get_role_permissions(self, role: Role) -> list[Permission]:
        return sorted(ROLE_PERMISSIONS.get(role, set()))

    def has_role(self, user_id: str, role: Role) -> bool:
        return role in self._user_roles.get(user_id, set())

    def list_users_with_role(self, role: Role) -> list[str]:
        return sorted(uid for uid, roles in self._user_roles.items() if role in roles)
