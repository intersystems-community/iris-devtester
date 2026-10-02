"""Constants and the frozen start options shared by ``load`` and ``build``."""

from dataclasses import dataclass, field
from typing import Dict, Optional

BUILD_TIMEOUT = 900
LOAD_TIMEOUT = 300
HEALTH_TIMEOUT = 120
RUN_TIMEOUT = 60
KILL_GRACE = 3

# Label keys written onto every container idt creates (the only definition).
LABEL_CREATED_BY = "io.iris-devtester.created-by"
LABEL_CREATED_BY_VALUE = "idt"
LABEL_IMAGE = "io.iris-devtester.image"

DEFAULT_PASSWORD = "SYS"
LICENSE_MOUNT_TARGET = "/usr/irissys/mgr/iris.key"


def build_labels(image_ref: str) -> Dict[str, str]:
    """Labels identifying a container as created by idt from ``image_ref``."""
    return {LABEL_CREATED_BY: LABEL_CREATED_BY_VALUE, LABEL_IMAGE: image_ref}


@dataclass(frozen=True)
class StartOptions:
    """Everything needed to create and start a container from an image."""

    name: str
    superserver_port: int
    web_port: Optional[int]
    password: str
    show_password: bool = False
    no_unexpire: bool = False
    health_timeout: int = HEALTH_TIMEOUT
    run_timeout: int = RUN_TIMEOUT
    labels: Dict[str, str] = field(default_factory=dict)
    license_mount: Optional[str] = None
    replace: bool = False
    cap_ipc_lock: bool = False
