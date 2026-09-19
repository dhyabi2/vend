"""Tests for the free trial system."""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trial_tracker import TrialTracker, reset_tracker_for_testing


def test_trial_tracker_basic():
    """A fresh IP has 5 remaining calls."""
    t = TrialTracker(max_free=5, window_sec=86400)
    assert t.remaining("1.2.3.4") == 5
    assert t.consume("1.2.3.4") is True
    assert t.remaining("1.2.3.4") == 4
    assert t.consume("1.2.3.4") is True
    assert t.remaining("1.2.3.4") == 3
    print("PASS test_trial_tracker_basic")


def test_trial_tracker_exhaustion():
    """After 5 consumes, remaining is 0 and consume returns False."""
    t = TrialTracker(max_free=5, window_sec=86400)
    for i in range(5):
        assert t.consume("5.6.7.8") is True
        assert t.remaining("5.6.7.8") == 4 - i
    assert t.consume("5.6.7.8") is False
    assert t.remaining("5.6.7.8") == 0
    print("PASS test_trial_tracker_exhaustion")


def test_trial_tracker_per_ip():
    """Different IPs have independent counters."""
    t = TrialTracker(max_free=3, window_sec=86400)
    assert t.consume("10.0.0.1") is True
    assert t.consume("10.0.0.2") is True
    assert t.consume("10.0.0.1") is True
    assert t.consume("10.0.0.1") is True
    assert t.consume("10.0.0.1") is False  # IP 1 exhausted (3 max)
    assert t.consume("10.0.0.2") is True   # IP 2 still has 2 left
    assert t.consume("10.0.0.2") is True
    assert t.consume("10.0.0.2") is False  # IP 2 exhausted
    print("PASS test_trial_tracker_per_ip")


def test_trial_tracker_window():
    """Calls older than window_sec don't count against the limit."""
    t = TrialTracker(max_free=2, window_sec=5)  # 5-second window
    assert t.consume("192.168.1.1") is True
    assert t.remaining("192.168.1.1") == 1
    # Wait for the window to pass
    time.sleep(6)
    # Old calls are now pruned
    assert t.remaining("192.168.1.1") == 2
    assert t.consume("192.168.1.1") is True
    print("PASS test_trial_tracker_window")


def test_trial_singleton():
    """reset_tracker_for_testing gives a fresh tracker."""
    from trial_tracker import get_tracker
    t1 = get_tracker()
    t1.consume("10.0.0.1")
    reset_tracker_for_testing()
    t2 = get_tracker()
    assert t2.remaining("10.0.0.1") == 5  # Fresh counter
    print("PASS test_trial_singleton")


if __name__ == "__main__":
    test_trial_tracker_basic()
    test_trial_tracker_exhaustion()
    test_trial_tracker_per_ip()
    test_trial_tracker_window()
    test_trial_singleton()
    print("\nAll trial tracker tests PASSED")