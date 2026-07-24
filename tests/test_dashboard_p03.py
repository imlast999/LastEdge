import sys
from unittest.mock import MagicMock

# Mock MetaTrader5 module if not present in python environment
if 'MetaTrader5' not in sys.modules:
    mt5_mock = MagicMock()
    mt5_mock.positions_get.return_value = []
    mt5_mock.account_info.return_value = None
    mt5_mock.symbol_info_tick.return_value = None
    sys.modules['MetaTrader5'] = mt5_mock

import pytest
import threading
import time
import json
import urllib.request
from datetime import datetime, timezone
from services.dashboard import DashboardService, SignalEvent, ReusableThreadingHTTPServer


def test_dashboard_thread_safety_concurrency():
    """Verify thread-safe reads, writes, shallow copies, and cleanup under high concurrency."""
    service = DashboardService()
    service.dashboard_config['enable_persistence'] = False

    # Pre-fill some signals
    for i in range(50):
        service.add_signal_event("EURUSD", "TestStrat", "BUY", "HIGH", 0.85, True, entry=1.08, sl=1.075, tp=1.09)

    errors = []

    def worker_add():
        try:
            for _ in range(50):
                service.add_signal_event("XAUUSD", "GoldStrat", "SELL", "HIGH", 0.9, True, entry=2000.0, sl=2010.0, tp=1980.0)
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"worker_add error: {e}")

    def worker_read_metrics():
        try:
            for _ in range(50):
                m = service.get_current_metrics()
                assert isinstance(m, dict)
                assert 'signals' in m
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"worker_read_metrics error: {e}")

    def worker_read_history():
        try:
            for _ in range(50):
                h = service.get_signal_history(hours=24)
                assert isinstance(h, list)
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"worker_read_history error: {e}")

    def worker_read_data():
        try:
            for _ in range(50):
                d = service.get_dashboard_data()
                assert isinstance(d, dict)
                assert 'equity_pts' in d
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"worker_read_data error: {e}")

    def worker_cleanup():
        try:
            for _ in range(10):
                service._cleanup_old_data()
                service._save_persisted_data()
                time.sleep(0.005)
        except Exception as e:
            errors.append(f"worker_cleanup error: {e}")

    threads = [
        threading.Thread(target=worker_add),
        threading.Thread(target=worker_add),
        threading.Thread(target=worker_read_metrics),
        threading.Thread(target=worker_read_history),
        threading.Thread(target=worker_read_data),
        threading.Thread(target=worker_cleanup),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrency errors encountered: {errors}"
    metrics = service.get_current_metrics()
    assert metrics['signals']['today'] >= 150


def test_dashboard_http_server_lifecycle_and_endpoints(monkeypatch):
    """Test HTTPServer startup, endpoint requests with JSON default=str, and clean shutdown."""
    port = 8899
    monkeypatch.setenv('DASHBOARD_PORT', str(port))
    monkeypatch.setenv('DISABLE_DASHBOARD', '0')

    service = DashboardService()
    service.dashboard_config['enable_persistence'] = False
    service.start()

    time.sleep(0.3)

    try:
        assert service.server_instance is not None
        assert isinstance(service.server_instance, ReusableThreadingHTTPServer)

        # Test /api/metrics
        req = urllib.request.urlopen(f"http://localhost:{port}/api/metrics")
        assert req.status == 200
        data = json.loads(req.read().decode('utf-8'))
        assert 'signals' in data

        # Test /api/data
        req_data = urllib.request.urlopen(f"http://localhost:{port}/api/data")
        assert req_data.status == 200
        dash_data = json.loads(req_data.read().decode('utf-8'))
        assert 'equity_pts' in dash_data
        assert 'session_signals' in dash_data

        # Test /api/equity
        req_eq = urllib.request.urlopen(f"http://localhost:{port}/api/equity")
        assert req_eq.status == 200
        eq_data = json.loads(req_eq.read().decode('utf-8'))
        assert 'total_equity' in eq_data

        # Test /api/execution-status
        req_exec = urllib.request.urlopen(f"http://localhost:{port}/api/execution-status")
        assert req_exec.status == 200
        exec_data = json.loads(req_exec.read().decode('utf-8'))
        assert 'auto_execute' in exec_data

    finally:
        service.stop()
        time.sleep(0.2)
        assert service.server_instance is None


def test_dashboard_frontend_html_no_reload():
    """Verify HTML generation removes location.reload() and includes dynamic fetch update loop."""
    service = DashboardService()
    html = service.get_dashboard_html(lang='en')

    # Ensure location.reload() is removed
    assert 'location.reload' not in html

    # Ensure dynamic JS update loop and Chart.js dataset update in-place are present
    assert 'fetchDashboardUpdate' in html
    assert 'setInterval(fetchDashboardUpdate, 10000)' in html
    assert 'equityChart.update' in html
    assert 'applyFilter()' in html
    assert 'stat-sys-status' in html
    assert 'stat-winrate' in html
