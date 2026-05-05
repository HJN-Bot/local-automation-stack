I couldn’t create `/tmp/mae_demo_test/hello.py` because this session is running with a read-only filesystem sandbox and approval is disabled.

The file content to create is:

```python
"""Simple command-line entry point for the MAE demo."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Print the MAE greeting.")
    return parser.parse_args()


def main() -> None:
    """Run the command."""
    parse_args()
    print("Hello MAE!")


if __name__ == "__main__":
    main()
```
