# Quickstart: verifying feature 036

1. Probe: `pytest tests/integration/test_base_quoted_password.py -m integration` (needs Docker); confirms the environment transfer and a quoted password.
2. Validation: `pytest tests/unit/test_iris_base_container.py -k "validation or quoting"`.
3. Licence policy: `pytest tests/unit/test_iris_base_container.py -k licence`.
4. Dead code: `grep -rn "HAS_TESTCONTAINERS\|_IRISMockContainer\|_ActualBase\|IRISBase\|driver=" iris_devtester tests` returns nothing relevant.
5. Labels: `idt container up ...` then `docker inspect --format '{{json .Config.Labels}}' <name>` shows both keys.
6. Coverage: `pytest tests/unit -m "not integration and not e2e"` passes with the 90% gate.
