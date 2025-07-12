# Unit Tests for BurnOut Application

This directory contains unit tests for the BurnOut application components.

## Running Tests

From the `app` directory, run:

```bash
source ../.venv/bin/activate
python run_tests.py
```

Or run individual test files:

```bash
python -m unittest tests.test_frustum_intersection
```

## Test Coverage

### test_frustum_intersection.py

Tests for the camera frustum-ground intersection calculations used in the footprint visualization feature:

- **TestFrustumGroundIntersection**: Tests the `compute_frustum_ground_intersection()` function with various camera orientations:
  - Camera looking straight down
  - Camera looking up (no intersection)
  - Camera at angles
  - Custom ground plane heights
  - Horizontal cameras
  - Different field of view angles
  - Edge cases and boundary conditions
  - Polygon ordering and symmetry

- **TestFrustumPlaneGeneration**: Tests VTK frustum plane generation and integration:
  - Frustum plane format validation
  - VTK frustum source integration
  - Coordinate system validation

## Test Philosophy

These tests use real VTK components rather than mocks, since VTK is a stable, well-tested library that should work reliably. This approach provides better integration testing and catches real-world issues.

## Adding New Tests

When adding new features:

1. Create test files following the naming convention `test_<feature>.py`
2. Use descriptive test method names starting with `test_`
3. Include docstrings explaining what each test validates
4. Test both normal cases and edge cases
5. Use real dependencies rather than mocks where practical