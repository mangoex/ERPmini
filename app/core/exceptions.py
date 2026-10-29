"""Jerarquía de excepciones de dominio para ERPmini."""


class DomainError(Exception):
    """Excepción base para todos los errores de dominio de la aplicación."""

    def __init__(self, message: str = "A domain error occurred"):
        super().__init__(message)
        self.message = message


class DomainValidationError(DomainError, ValueError):
    """Lanzada cuando una regla de validación de entidad o valor es violada."""


class FSMTransitionError(DomainError):
    """Lanzada cuando se intenta una transición de estado inválida en el motor FSM."""


class InsufficientStockError(DomainError):
    """Lanzada cuando no hay saldo de inventario suficiente en una ubicación interna/planta."""


class CreditLimitExceededError(DomainError):
    """Lanzada cuando una orden de venta excede el límite de crédito disponible del cliente."""


class ThreeWayMatchError(DomainError):
    """Lanzada cuando la factura de proveedor no coincide con la PO y la recepción en báscula (GRN)."""


class UnbalancedJournalError(DomainError):
    """Lanzada cuando un asiento contable no cumple con partida doble estricta (Debe != Haber)."""


class RBACPermissionDeniedError(DomainError):
    """Lanzada cuando el usuario o rol carece de los permisos explícitos requeridos."""


class ImmutableRecordError(DomainError):
    """Lanzada cuando se intenta mutar (UPDATE) o eliminar (DELETE) un registro inmutable."""
