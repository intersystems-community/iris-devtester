from click.testing import CliRunner

from iris_devtester.cli.image import image_group


def _labels(argv):
    return [argv[i + 1] for i, a in enumerate(argv) if a == "--label"]


def test_load_labels(fake_runner, fake_docker, fake_health, fake_password, image_archive):
    res = CliRunner().invoke(image_group, ["load", str(image_archive), "--name", "lb1"])
    assert res.exit_code == 0, res.output
    (argv,) = fake_runner.argvs("docker", "run")
    labels = _labels(argv)
    assert "io.iris-devtester.created-by=idt" in labels
    assert "io.iris-devtester.image=iris-test:1" in labels


def test_build_labels(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64
):
    res = CliRunner().invoke(
        image_group,
        [
            "build", str(installer_kit), "--platform", "linux/arm64",
            "--iris-main", str(elf_arm64), "--tag", "my-iris:9", "--name", "lb2",
        ],
    )  # fmt: skip
    assert res.exit_code == 0, res.output
    (argv,) = fake_runner.argvs("docker", "run")
    labels = _labels(argv)
    assert "io.iris-devtester.created-by=idt" in labels
    assert "io.iris-devtester.image=my-iris:9" in labels
    assert argv.count("--label") == 2
