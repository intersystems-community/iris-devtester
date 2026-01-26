"""Utility functions and helpers."""

from iris_devtester.utils.container_status import get_container_status
from iris_devtester.utils.enable_callin import enable_callin_service
from iris_devtester.utils.password import (
    ErrorType,
    PasswordResetResult,
    PasswordResult,
    VerificationConfig,
    VerificationResult,
    detect_password_change_required,
    reset_password,
    reset_password_if_needed,
    unexpire_all_passwords,
    unexpire_passwords_for_containers,
    verify_password,
    verify_password_via_connection,
)
from iris_devtester.utils.test_connection import test_connection

__all__ = [
    # Password utilities (consolidated)
    "detect_password_change_required",
    "reset_password",
    "reset_password_if_needed",
    "unexpire_all_passwords",
    "unexpire_passwords_for_containers",
    "verify_password",
    "verify_password_via_connection",
    # Password result types
    "ErrorType",
    "PasswordResetResult",
    "PasswordResult",
    "VerificationConfig",
    "VerificationResult",
    # Other utilities
    "enable_callin_service",
    "test_connection",
    "get_container_status",
]
