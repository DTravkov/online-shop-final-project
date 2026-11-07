class RecordNotFound(Exception):
    def __init__(self, entity: str, record_id: int):
        super().__init__(f"{entity} {record_id} not found")


class RecordConflict(Exception):
    pass


class UserNotFound(Exception):
    def __init__(self, user_id: int):
        super().__init__(f"User {user_id} not found")


class AuthenticationFailed(Exception):
    """Missing, invalid, or expired credentials (HTTP 401)."""


class PermissionDenied(Exception):
    """The authenticated account may not perform this operation (HTTP 403)."""


class BusinessRuleViolation(Exception):
    """The request is well-formed but breaks a marketplace rule (HTTP 400)."""
