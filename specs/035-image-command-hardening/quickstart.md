# Quickstart: verifying feature 035

1. Unit tests: `pytest tests/unit/image -m "not integration and not e2e" --cov=iris_devtester/cli/image --cov-fail-under=95`
2. Timeout: `idt image build kit.tar.gz --build-timeout 5` against a slow build; expect exit 5 within about 5 s.
3. Password: `idt image load archive.tar.gz`; summary shows `********`; add `--show-password` to see it.
4. Key: `idt image build kit.tar.gz --license ./iris.key`; `docker history <tag>` must not contain the key; `docker inspect` shows the read-only mount.
5. Collision: run `load` twice with the same `--name`; second run refuses with exit 2 and names `--replace`; add `--replace` to proceed.
6. iris-main: `idt image build kit.tar.gz --platform linux/amd64 --iris-main <arm64 binary>` exits 2 before building.
7. Integration (needs Docker): `pytest tests/integration/test_image_load_docker.py -m integration`.
