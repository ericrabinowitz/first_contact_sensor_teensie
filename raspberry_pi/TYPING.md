# Python Type Annotations

This document describes the type annotation setup for the Raspberry Pi Python code.

## Type Checking with pytype

We use Google's `pytype` for static type checking. It provides good type inference and catches common errors without requiring complete type annotations.

### Installation

```bash
make typecheck-install
# or
pip3 install pytype
```

### Running Type Checks

```bash
make typecheck
```

This will check all Python files in the `raspberry_pi` directory, excluding:
- Test files (`*_test.py`, `test_*.py`)
- Custom pattern files (contain visualization code with many undefined globals)
- Setup scripts
- Controller code (to be typed later)

### Configuration

Type checking is configured in `pytype.cfg`:
- Python version: 3.9
- Strict None binding enabled
- Import errors disabled (due to dynamic imports)
- Parallel processing enabled

## Type Annotation Guidelines

### Basic Types

```python
from typing import Dict, List, Optional, Union, Any, Callable

# Function annotations
def process_data(data: str, count: int = 0) -> bool:
    return True

# Variable annotations
devices: List[Dict[str, Any]] = []
callback: Optional[Callable[[int], np.ndarray]] = None
```

### Forward References

For circular imports, use string quotes or TYPE_CHECKING:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .link_state import LinkStateTracker
    from .display import StatusDisplay

def detect_tone(tracker: 'LinkStateTracker') -> None:
    pass
```

### Common Patterns in This Codebase

1. **Device Configuration**
```python
DeviceConfig = Dict[str, Any]  # Contains 'statue', 'device_index', etc.
devices: List[DeviceConfig] = configure_devices()
```

2. **Callback Functions**
```python
ToneGenerator = Callable[[int], np.ndarray]
tone_gen: ToneGenerator = create_tone_generator(frequency, sample_rate)
```

3. **Statue Enums**
```python
from audio.devices import Statue
statue: Statue = Statue.EROS
```

4. **NumPy Arrays**
```python
import numpy as np
audio_data: np.ndarray = np.zeros((1000, 2))
```

## Benefits

1. **Early Error Detection**: Catches type mismatches before runtime
2. **Better IDE Support**: Enables auto-completion and inline documentation
3. **Code Documentation**: Types serve as inline documentation
4. **Refactoring Safety**: Makes large refactors safer

## Next Steps

1. Add type annotations to controller module
2. Create type stubs for external libraries if needed
3. Consider using `mypy` for stricter checking
4. Add pre-commit hooks for type checking