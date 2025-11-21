from hcai_ops.testing.stress_test import run_stress_test, run_full_ingest_test


def test_run_stress_test_small():
    summary = run_stress_test({"type": "syslog", "events": 5, "rate": 50})
    assert summary["events"] > 0
    assert summary["eps"] > 0
    assert "duration" in summary
    assert "memory_bytes" in summary


def test_run_full_ingest_test():
    summary = run_full_ingest_test()
    assert summary["total_events"] > 0
    assert summary["valid"] is True
