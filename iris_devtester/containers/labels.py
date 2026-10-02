"""Docker labels that mark containers created by iris-devtester.

Defined once here; see specs/036-container-base-hardening/contracts/labels-contract.md.
Other features read these labels to decide which containers they may replace or remove.
The unrelated ``iris-devtester.config.source`` label is not touched.
"""

from typing import Dict, Optional

LABEL_CREATED_BY = "io.iris-devtester.created-by"
LABEL_CREATED_BY_VALUE = "idt"
LABEL_IMAGE = "io.iris-devtester.image"


def build_labels(image_ref: Optional[str]) -> Dict[str, str]:
    """Return the idt label set; the image label is omitted when the ref is unknown."""
    labels = {LABEL_CREATED_BY: LABEL_CREATED_BY_VALUE}
    if image_ref:
        labels[LABEL_IMAGE] = image_ref
    return labels
