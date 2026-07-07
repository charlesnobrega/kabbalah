"""Shared pytest configuration.

Many property tests in this suite do real filesystem/SQLite I/O per generated
example. Under full-suite CPU contention the default Hypothesis 200ms
per-example deadline is intermittently exceeded, producing flaky failures that
do not reproduce in isolation (observed in the governance and memory-subsystem
property files).

Disable the deadline suite-wide. The deadline is a latency guard, not a
correctness check: every assertion inside a property still runs, so a genuine
defect (e.g. a store returning False under a file lock) still fails the test.
Only timing-based flakiness is suppressed.
"""

from hypothesis import HealthCheck, settings

settings.register_profile(
    "kabbalah",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("kabbalah")
