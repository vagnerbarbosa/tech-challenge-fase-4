#!/usr/bin/env python3
"""Script CLI para gerar e registrar API keys.

Gera uma chave API via Python e registra automaticamente no sistema,
permitindo uso imediato sem necessidade de acessar o arquivo manualmente.

Uso:
    python scripts/generate-api-key.py
    python scripts/generate-api-key.py --description "Cliente XYZ"
"""

import argparse
import json
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path


# Configuração
STORAGE_PATH = Path(os.getenv("API_KEYS_PATH", "data/generated_api_keys.json"))


def ensure_storage_exists():
    """Cria diretório e arquivo se não existirem."""
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_PATH.exists():
        STORAGE_PATH.write_text("{}")
        import os
        os.chmod(STORAGE_PATH, 0o600)


def generate_api_key() -> tuple[str, str]:
    """Gera uma API key segura.

    Returns:
        Tupla (api_key, key_id)
    """
    raw_key = secrets.token_hex(32)
    api_key = f"ak_{raw_key}"
    key_id = raw_key[:16]
    return api_key, key_id


def register_key(api_key: str, description: str | None = None) -> str:
    """Registra a chave no arquivo.

    Args:
        api_key: A chave de API completa
        description: Descrição opcional

    Returns:
        key_id da chave registrada
    """
    ensure_storage_exists()

    raw_key = api_key.replace("ak_", "")
    key_id = raw_key[:16]

    # Carrega chaves existentes
    try:
        with open(STORAGE_PATH, "r") as f:
            keys = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        keys = {}

    # Registra nova chave
    keys[key_id] = {
        "api_key": api_key,
        "description": description or "Generated via CLI script",
        "created_at": datetime.now(UTC).isoformat(),
    }

    # Salva arquivo
    with open(STORAGE_PATH, "w") as f:
        json.dump(keys, f, indent=2)

    # Mantém permissões restritas
    import os
    os.chmod(STORAGE_PATH, 0o600)

    return key_id


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Gera e registra API key para o sistema Multimodal Health"
    )
    parser.add_argument(
        "--description",
        "-d",
        help="Descrição da chave (ex: 'Cliente Hospital XYZ')",
        default=None,
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Exibe chave completa (cuidado: redirecione para arquivo seguro)",
    )

    args = parser.parse_args()

    # Gera chave
    api_key, key_id = generate_api_key()

    # Registra no arquivo
    registered_id = register_key(api_key, args.description)

    # Output - Nunca exibe a chave completa no stdout (segurança CodeQL)
    print("=" * 70)
    print("API Key gerada e registrada com sucesso!")
    print("=" * 70)
    print(f"\nKey ID:    {registered_id}")
    print(f"Arquivo:   {STORAGE_PATH.absolute()}")
    if args.description:
        print(f"Descrição: {args.description}")
    print("\n" + "=" * 70)
    print("⚠️  ATENÇÃO: A chave está armazenada no arquivo acima.")
    print("    Leia o arquivo diretamente com: sudo cat", STORAGE_PATH.absolute())
    print("    Arquivo tem permissão 0o600 (apenas owner).")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
