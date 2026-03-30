#!/usr/bin/env python3
"""Local sanity check: CUDA availability and (optional) tribev2 import.

Full TRIBE v2 inference needs a Linux GPU machine with HF token; use Modal for end-to-end tests.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import torch
    except ImportError:
        print("PyTorch not installed locally; skip GPU check. Deploy with: modal deploy app.py")
        return 0

    cuda = torch.cuda.is_available()
    print(f"torch {torch.__version__}, cuda_available={cuda}")
    if cuda:
        print(f"device: {torch.cuda.get_device_name(0)}")
    else:
        print(
            "No local CUDA — expected on macOS. Run inference on Modal after "
            "`modal secret create hf-secret HUGGING_FACE_HUB_TOKEN=...` "
            "and `modal deploy app.py`."
        )

    try:
        import tribev2  # noqa: F401

        print("tribev2 import OK (optional local install).")
    except ImportError:
        print("tribev2 not installed locally (normal); image installs it on Modal.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
