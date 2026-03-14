# Run tests

Runs the full test suite and reports results.

## Steps

1. Run JS unit tests:
   ```
   npx jest --testPathPattern="tests/unit" --verbose
   ```

2. Run Python tests:
   ```
   python3 -m pytest tests/python/ -v
   ```

3. Run integration tests:
   ```
   npx playwright test tests/integration/app.spec.js
   ```

4. Report a summary: total passed / failed across all three suites (expected: 205 tests, all green).

If any tests fail, read the error output carefully and diagnose before attempting fixes. Do not re-run failing tests in a loop — investigate the root cause first.
