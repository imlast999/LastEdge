"""
LastEdge — Private Strategy Vault Synchronization Utility
scripts/sync_vault.py
=========================================================
Sincroniza bidireccionalmente las estrategias privadas entre el repositorio maestro
independiente (C:\\LastEdge\\LastEdge-Private-Strategies) y las carpetas por par
del Trading Engine y Strategy Lab (strategies/<SYMBOL>/).

Uso:
    python scripts/sync_vault.py --pull     # Copia del Vault maestro a las carpetas por par
    python scripts/sync_vault.py --push     # Copia de las carpetas por par al Vault maestro
    python scripts/sync_vault.py --status   # Compara el estado de los archivos
"""

from __future__ import annotations

import os
import sys
import shutil
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Rutas canónicas
ROOT_DIR = Path(r"C:\LastEdge")
VAULT_REPO = ROOT_DIR / "LastEdge-Private-Strategies"
ENGINE_STRATEGIES = ROOT_DIR / "LastEdge Trading Engine" / "strategies"
LAB_STRATEGIES = ROOT_DIR / "LastEdge Strategy Lab" / "strategies"

# Mapeo de archivos privados por par (excluye archivos públicos)
PRIVATE_STRATEGY_MAP = {
    "EURUSD": [
        "eurusd.py",
        "eurusd_partial.py",
        "eurusd_flow.py",
        "eurusd_london_expansion.py",
    ],
    "XAUUSD": [
        "xauusd.py",
        "xauusd_asian_london.py",
        "xauusd_partial.py",
        "xauusd_statistical_reversal.py",
        "xauusd_surge.py",
    ],
    "BTCEUR": [
        "btceur_new.py",
        "btceur_partial.py",
        "btceur_trend_surge.py",
        "btceur_volatility_breakout.py",
    ]
}

def file_hash(path: Path) -> str:
    """Calcula SHA-256 de un archivo."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sync_pull():
    """Copia archivos del Vault maestro hacia las carpetas por par del Engine y Lab."""
    print("=" * 70)
    print("📥 PULL: Sincronizando desde LastEdge-Private-Strategies hacia Engine y Lab...")
    print("=" * 70)

    if not VAULT_REPO.exists():
        print(f"❌ Error: El repositorio {VAULT_REPO} no existe.")
        return False

    copied_count = 0
    targets = [("Trading Engine", ENGINE_STRATEGIES), ("Strategy Lab", LAB_STRATEGIES)]

    for pair, files in PRIVATE_STRATEGY_MAP.items():
        for filename in files:
            src_file = VAULT_REPO / filename
            if not src_file.exists():
                continue

            for target_name, target_base in targets:
                dest_dir = target_base / pair
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / filename

                # Solo copiar si el archivo destino no existe o tiene hash diferente
                if not dest_file.exists() or file_hash(src_file) != file_hash(dest_file):
                    shutil.copy2(src_file, dest_file)
                    print(f"  ✅ [{target_name}] Copiado {pair}/{filename}")
                    copied_count += 1

    print(f"\n🎉 Pull completado: {copied_count} actualizaciones aplicadas.")
    return True

def sync_push():
    """Copia archivos actualizados desde las carpetas por par hacia el Vault maestro."""
    print("=" * 70)
    print("📤 PUSH: Sincronizando cambios locales hacia LastEdge-Private-Strategies...")
    print("=" * 70)

    if not VAULT_REPO.exists():
        print(f"❌ Error: El repositorio {VAULT_REPO} no existe.")
        return False

    updated_count = 0

    # Usar el Trading Engine como fuente principal de cambios locales
    for pair, files in PRIVATE_STRATEGY_MAP.items():
        for filename in files:
            src_file = ENGINE_STRATEGIES / pair / filename
            if not src_file.exists():
                # Fallback al Strategy Lab si no está en el Engine
                src_file = LAB_STRATEGIES / pair / filename

            if not src_file.exists():
                continue

            dest_file = VAULT_REPO / filename

            # Si es nuevo o diferente, copiar al Vault maestro
            if not dest_file.exists() or file_hash(src_file) != file_hash(dest_file):
                shutil.copy2(src_file, dest_file)
                print(f"  ✅ Actualizado en Vault maestro: {filename} (desde {pair})")
                updated_count += 1

    # También detectar si el usuario creó una nueva estrategia privada en alguna carpeta por par
    for pair_dir in ENGINE_STRATEGIES.iterdir():
        if not pair_dir.is_dir() or pair_dir.name.startswith((".", "_")):
            continue
        if pair_dir.name.lower() in ("public", "vault", "private", "archive", "tests", "scripts"):
            continue

        pair_name = pair_dir.name.upper()
        for py_path in pair_dir.glob("*.py"):
            if py_path.name.startswith(("_", ".")) or py_path.name.endswith("_test.py"):
                continue
            if "_public_" in py_path.name:
                continue  # Omitir estrategias públicas

            vault_target = VAULT_REPO / py_path.name
            if not vault_target.exists() or file_hash(py_path) != file_hash(vault_target):
                shutil.copy2(py_path, vault_target)
                print(f"  ✨ Nueva estrategia detectada y agregada al Vault: {py_path.name} (par {pair_name})")
                updated_count += 1

    print(f"\n🎉 Push completado: {updated_count} archivos actualizados en {VAULT_REPO.name}")
    print("\nPuedes revisar y commitear los cambios con:")
    print(f'  cd "{VAULT_REPO}" && git status')
    return True

def sync_status():
    """Muestra el estado de sincronización entre el Vault y los motores."""
    print("=" * 70)
    print("🔍 STATUS: Comparando archivos entre Vault y motores locales...")
    print("=" * 70)

    for pair, files in PRIVATE_STRATEGY_MAP.items():
        print(f"\n📂 Par: {pair}")
        for filename in files:
            vault_file = VAULT_REPO / filename
            engine_file = ENGINE_STRATEGIES / pair / filename
            lab_file = LAB_STRATEGIES / pair / filename

            v_hash = file_hash(vault_file)[:8] if vault_file.exists() else "NO EXISTE"
            e_hash = file_hash(engine_file)[:8] if engine_file.exists() else "NO EXISTE"
            l_hash = file_hash(lab_file)[:8] if lab_file.exists() else "NO EXISTE"

            status = "🟢 SINCRONIZADO" if (v_hash == e_hash == l_hash and v_hash != "NO EXISTE") else "🟡 DIFERENTE"
            print(f"  • {filename:<32} | Vault: {v_hash:<10} | Engine: {e_hash:<10} | Lab: {l_hash:<10} | {status}")

def main():
    parser = argparse.ArgumentParser(description="LastEdge Private Strategy Vault Sync Tool")
    parser.add_argument("--pull", action="store_true", help="Sincronizar del Vault hacia Engine y Lab")
    parser.add_argument("--push", action="store_true", help="Sincronizar de Engine/Lab hacia el Vault")
    parser.add_argument("--status", action="store_true", help="Ver estado de sincronización")

    args = parser.parse_args()

    if args.pull:
        sync_pull()
    elif args.push:
        sync_push()
    elif args.status:
        sync_status()
    else:
        # Por defecto muestra el estado
        sync_status()

if __name__ == "__main__":
    main()
