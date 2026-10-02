import pytest

from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.iris_main import check_elf_arch


def test_accepts_arm64_for_arm64(elf_arm64):
    assert check_elf_arch(elf_arm64, "linux/arm64") == "arm64"


def test_accepts_amd64_for_amd64(elf_amd64):
    assert check_elf_arch(elf_amd64, "linux/amd64") == "amd64"


@pytest.mark.parametrize("plat", ["linux/arm64/v8", "linux/aarch64"])
def test_platform_spellings_arm64(elf_arm64, plat):
    assert check_elf_arch(elf_arm64, plat) == "arm64"


@pytest.mark.parametrize("plat", ["linux/x86_64", "linux/amd64/v2"])
def test_platform_spellings_amd64(elf_amd64, plat):
    assert check_elf_arch(elf_amd64, plat) == "amd64"


def test_mismatch_names_both_architectures(elf_arm64):
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(elf_arm64, "linux/amd64")
    err = ei.value
    assert err.exit_code == 2
    assert "arm64" in err.what and "amd64" in err.what
    assert "docker create --platform linux/amd64" in err.fix


def test_truncated_file(tmp_path):
    p = tmp_path / "iris-main"
    p.write_bytes(b"\x7fELF\x02\x01")
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(p, "linux/arm64")
    assert ei.value.exit_code == 2
    assert "not a valid" in ei.value.what.lower()


def test_empty_file(tmp_path):
    p = tmp_path / "iris-main"
    p.write_bytes(b"")
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(p, "linux/arm64")
    assert ei.value.exit_code == 2


def test_not_elf(tmp_path):
    p = tmp_path / "iris-main"
    p.write_bytes(b"#!/bin/sh\necho hi there friend\n")
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(p, "linux/arm64")
    assert "not a valid" in ei.value.what.lower()


def test_32_bit_elf_rejected(tmp_path):
    hdr = bytearray(20)
    hdr[0:4] = b"\x7fELF"
    hdr[4], hdr[5] = 1, 1
    hdr[18:20] = (0xB7).to_bytes(2, "little")
    p = tmp_path / "iris-main"
    p.write_bytes(bytes(hdr))
    with pytest.raises(ImageCommandError):
        check_elf_arch(p, "linux/arm64")


def test_big_endian_rejected(tmp_path):
    hdr = bytearray(20)
    hdr[0:4] = b"\x7fELF"
    hdr[4], hdr[5] = 2, 2
    p = tmp_path / "iris-main"
    p.write_bytes(bytes(hdr))
    with pytest.raises(ImageCommandError):
        check_elf_arch(p, "linux/arm64")


def test_os_abi_byte_is_not_asserted(tmp_path, elf_arm64):
    data = bytearray(elf_arm64.read_bytes())
    data[7] = 3  # ELFOSABI_GNU
    p = tmp_path / "iris-main-gnu"
    p.write_bytes(bytes(data))
    assert check_elf_arch(p, "linux/arm64") == "arm64"


def test_unknown_machine_rejected(tmp_path):
    hdr = bytearray(20)
    hdr[0:4] = b"\x7fELF"
    hdr[4], hdr[5] = 2, 1
    hdr[18:20] = (0xF3).to_bytes(2, "little")  # RISC-V
    p = tmp_path / "iris-main"
    p.write_bytes(bytes(hdr))
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(p, "linux/arm64")
    assert "0xf3" in ei.value.what.lower()


def test_unsupported_platform(elf_arm64):
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(elf_arm64, "linux/riscv64")
    assert ei.value.exit_code == 2


def test_missing_file(tmp_path):
    with pytest.raises(ImageCommandError) as ei:
        check_elf_arch(tmp_path / "nope", "linux/arm64")
    assert ei.value.exit_code == 2
