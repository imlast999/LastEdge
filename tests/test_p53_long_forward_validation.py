"""
Tests para P5.3 — Long Forward Validation & Longevity Engine
============================================================
Verifica el monitoreo de memoria, la tasa de variación (slope),
el registro de anomalías y la resiliencia ante reconexiones.
"""

from __future__ import annotations

import os
import unittest
import tempfile
from services.database import get_database_manager
from services.long_forward_validation import (
    LongForwardValidationService,
    get_long_forward_validation_service,
)
from services.bot_service import BotService


class TestP53LongForwardValidation(unittest.TestCase):

    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db_path = self.tmp_db.name
        self.db_manager = get_database_manager(self.db_path)
        self.svc = LongForwardValidationService(self.db_path)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_record_sample_and_slope(self):
        # Grabar muestras de prueba con leve incremento
        self.svc.record_sample(rss_mb=100.0, vms_mb=200.0, cpu_pct=1.0)
        self.svc.record_sample(rss_mb=102.0, vms_mb=202.0, cpu_pct=1.1)
        self.svc.record_sample(rss_mb=104.0, vms_mb=204.0, cpu_pct=1.2)

        report = self.svc.get_validation_report()
        self.assertEqual(report["verdict"], "STABLE")
        self.assertEqual(report["memory_telemetry"]["total_samples"], 3)
        self.assertEqual(report["memory_telemetry"]["min_rss_mb"], 100.0)
        self.assertEqual(report["memory_telemetry"]["max_rss_mb"], 104.0)

    def test_anomaly_logging_and_reconnection(self):
        self.svc.log_reconnection(source="MT5_SERVER_DEMO")
        self.svc.log_failure_recovery(subsystem="TradeJournal", detail="SQLite WAL Busy Auto-retry OK")

        report = self.svc.get_validation_report()
        self.assertEqual(report["resilience_telemetry"]["reconnections_total"], 1)
        self.assertEqual(report["resilience_telemetry"]["failures_recovered_total"], 1)
        self.assertEqual(len(report["anomalies"]), 2)

    def test_session_lifecycle(self):
        res_start = self.svc.start_session(profile="72h")
        self.assertTrue(res_start["ok"])
        self.assertTrue(self.svc.session_active)
        self.assertEqual(self.svc.session_profile, "72h")

        res_stop = self.svc.stop_session()
        self.assertTrue(res_stop["ok"])
        self.assertFalse(self.svc.session_active)

    def test_bot_service_integration(self):
        bot_svc = BotService()
        status = bot_svc.get_long_forward_status()
        self.assertIn("verdict", status)
        self.assertIn("memory_telemetry", status)

        start_res = bot_svc.start_long_forward_session("24h")
        self.assertTrue(start_res["ok"])

        stop_res = bot_svc.stop_long_forward_session()
        self.assertTrue(stop_res["ok"])


if __name__ == "__main__":
    unittest.main()
