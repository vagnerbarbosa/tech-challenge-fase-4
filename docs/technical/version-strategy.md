# Estratégia de Versionamento Centralizado

## Problema
A versão da aplicação está espalhada em múltiplos arquivos:
- pyproject.toml
- src/core/config.py
- docker-compose.yml
- docker-compose.mock.yml
- .env.example
- README.md
- docs/PROJECT_STATUS.md
- docs/api-contracts.md
- specs/*/contracts/*.md

## Solução Proposta

### 1. Fonte Única de Verdade: `pyproject.toml`
```toml
[tool.poetry]
version = "0.9.0"  # ← Único lugar para definir a versão
```

### 2. Código Python: Ler dinamicamente de pyproject.toml
```python
# src/core/config.py
import tomllib
from pathlib import Path

def get_version() -> str:
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["version"]
```

### 3. Docker: Build args ou environment
```yaml
# docker-compose.yml
services:
  app:
    build:
      args:
        - APP_VERSION=${APP_VERSION:-0.9.0}
    environment:
      - APP_VERSION=${APP_VERSION:-0.9.0}
```

Ou usar um script de build que lê do pyproject.toml:
```bash
#!/bin/bash
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
export APP_VERSION=$VERSION
docker-compose up --build
```

### 4. Documentação: Usar placeholders
Usar comentários ou scripts de pre-commit para atualizar automaticamente.

### 5. CI/CD: Extrair do pyproject.toml
```yaml
- name: Get version
  run: |
    VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "APP_VERSION=$VERSION" >> $GITHUB_ENV
```

## Implementação Sugerida

1. **Configuração Python**: Usar `importlib.metadata` (padrão Python 3.8+)
   ```python
   from importlib.metadata import version
   APP_VERSION = version("multimodal-health-analysis")
   ```

2. **Docker**: Passar como build arg no CI

3. **Docs**: Usar mkdocs hooks ou pre-commit para substituir placeholders

## Benefícios
- Single source of truth
- Nunca esquecer de atualizar um arquivo
- Versionamento consistente entre todos os componentes
