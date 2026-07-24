import pytest
import pandas as pd
import numpy as np

import signals
from signals import (
    _get_eurusd_asian_breakout,
    _get_xauusd_psychological,
    _get_eurusd_mtf,
    STRATEGY_REGISTRY,
    get_available_strategies,
    detect_signal
)


def test_experimental_strategy_imports():
    asian = _get_eurusd_asian_breakout()
    assert asian.__module__ == 'strategies.experimental.eurusd_asian_breakout'
    assert asian.__class__.__name__ == 'EURUSDAsianBreakoutStrategy'

    psych = _get_xauusd_psychological()
    assert psych.__module__ == 'strategies.experimental.xauusd_psychological'
    assert psych.__class__.__name__ == 'XAUUSDPsychologicalStrategy'

    mtf = _get_eurusd_mtf()
    assert mtf.__module__ == 'strategies.experimental.eurusd_mtf'
    assert mtf.__class__.__name__ == 'EURUSDMultiTimeframeStrategy'


def test_rsi_macd_fallbacks_removed():
    assert 'rsi' not in STRATEGY_REGISTRY
    assert 'macd' not in STRATEGY_REGISTRY


def test_all_registry_factories_instantiate():
    for name, factory in STRATEGY_REGISTRY.items():
        inst = factory()
        assert inst is not None, f"Factory for '{name}' returned None"


def test_btceur_partial_strategy_valid_and_executable():
    dates = pd.date_range("2026-01-01", periods=50, freq="1h")
    df_sample = pd.DataFrame({
        'time': dates,
        'open': np.random.uniform(50000, 51000, 50),
        'high': np.random.uniform(51000, 52000, 50),
        'low': np.random.uniform(49000, 50000, 50),
        'close': np.random.uniform(50000, 51000, 50),
        'tick_volume': np.random.randint(100, 1000, 50)
    })

    sig, df_out = detect_signal(df_sample, strategy='btceur', symbol='BTCEUR')
    # Execution should not raise exception or hit invalid strategy class critical abort
    assert df_out is not None
