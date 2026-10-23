"""Tests for permission checks and the confirmation flow."""
import pytest

from security.confirmation import ConfirmationService
from security.permissions import PermissionManager
from security.policies import PermissionLevel
from utils.exceptions import PermissionDeniedError


def test_safe_action_allowed_without_confirmation():
    manager = PermissionManager(ConfirmationService())
    decision = manager.check("get_battery_status", PermissionLevel.SAFE, "battery", "read battery")
    assert decision.allowed and not decision.needs_confirmation


def test_confirm_level_requires_confirmation():
    manager = PermissionManager(ConfirmationService())
    decision = manager.check("delete_files", PermissionLevel.CONFIRM, "delete", "delete 3 files")
    assert decision.needs_confirmation
    assert decision.confirmation is not None


def test_high_risk_blocked_by_default():
    manager = PermissionManager(ConfirmationService(), high_risk_enabled=False)
    with pytest.raises(PermissionDeniedError):
        manager.check("registry_edit", PermissionLevel.HIGH_RISK, "registry", "edit registry")


def test_confirmation_resolution_yes_no():
    service = ConfirmationService()
    req = service.request("delete", "delete 3 files")
    assert service.resolve_from_speech(req.id, "yes please") is True
    assert service.get(req.id).approved is True

    req2 = service.request("delete", "delete 3 files")
    assert service.resolve_from_speech(req2.id, "no, cancel that") is True
    assert service.get(req2.id).approved is False
