# Testing

pytest + pytest-django. Shared fixtures live in the project-level
`conftest.py` — plain fixtures, no factory-boy. Fixtures never depend on the seed command; the seed's own tests in `products/tests.py` invoke it directly.
The suite must be green at every phase boundary.
