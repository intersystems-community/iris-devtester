# Tasks: 034-cpf-first-password-strategy

**Branch**: `034-cpf-first-password-strategy` | Generated: 2026-04-25

## Wave 1 — iris_container.py changes

- [ ] **T1** `__init__`: add `self._password_handled: bool = False`

- [ ] **T2** `start()`: inject `CPFPreset.SECURE_DEFAULTS` via CPF merge before `super().start()`
  - Check `getattr(self, "_cpf_merge_file", None)` — skip if user already set a merge file
  - If `self._preconfigure_password` is set: build merged CPF with PasswordHash line + ChangePassword=0
  - If not: use `CPFPreset.SECURE_DEFAULTS` as-is
  - Call `self.with_cpf_merge(cpf_content)`
  - Set `self._password_handled = True`

- [ ] **T3** `get_connection()`: optimistic connect, fallback on error
  - Remove proactive `unexpire_all_passwords()` call
  - Attempt `get_connection(config)` directly
  - If `ConnectionError` with password-change indicator AND NOT `_password_handled`:
    - call `unexpire_all_passwords(container_name)` 
    - set `_password_handled = True`
    - retry once
  - If `ConnectionError` with password-change indicator AND `_password_handled`:
    - raise with full diagnostic including `idt container reset-password`

## Wave 2 — dbapi.py tighten error message

- [ ] **T4** `connections/dbapi.py`: include `container_name` hint in password-change error message
  - Current message says `reset_password_if_needed(e, username='_SYSTEM')` — missing `container_name`
  - New: `reset_password_if_needed(e, container_name='<container-name>', username='_SYSTEM')`
  - Or: `idt container reset-password <container-name>`

## Wave 3 — Contract tests

- [ ] **T5** `tests/contract/test_034_cpf_password.py`
  - `test_start_injects_cpf_merge`: mock `with_cpf_merge`, verify called with SECURE_DEFAULTS content
  - `test_start_skips_cpf_if_already_set`: if `_cpf_merge_file` present, `with_cpf_merge` not called again
  - `test_start_sets_password_handled_true`: after start(), `_password_handled` is True
  - `test_get_connection_no_unexpire_on_success`: on clean connect, `unexpire_all_passwords` never called
  - `test_get_connection_fallback_on_password_error`: password-change error → unexpire → retry
  - `test_get_connection_no_double_fallback`: second error with `_password_handled=True` → raises directly

## Wave 4 — Regression

- [ ] **T6** `pytest tests/unit/ --override-ini="addopts=" -q` → 386 pass
