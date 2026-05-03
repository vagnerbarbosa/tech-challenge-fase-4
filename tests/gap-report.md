# Relatório de Gaps de Cobertura de Testes

**Gerado em**: 2026-05-03  
**Cobertura Atual**: 81.61% (meta: 90%)  
**Gap para Meta**: ~330 statements

---

## Resumo por Módulo

| Módulo | Stmts | Miss | Cover | Status |
|--------|-------|------|-------|--------|
| `src/api/routes/multimodal.py` | 111 | 51 | **54%** | 🔴 Crítico |
| `src/api/routes/audio.py` | 85 | 19 | **78%** | 🟡 Melhorar |
| `src/api/routes/video.py` | 86 | 5 | **94%** | 🟢 Bom |
| `src/utils/file_validation.py` | 133 | 52 | **61%** | 🔴 Crítico |
| `src/utils/audit_logger.py` | 243 | 79 | **67%** | 🟡 Melhorar |

---

## Detalhes dos Gaps

### 1. Rotas da API

#### `src/api/routes/multimodal.py` (54%)
**Linhas não cobertas:**
- 121-126: Tratamento de erro de rate limit
- 141-161: Tratamento de erro de quota excedida
- 168-196: Tratamento de erro de timeout
- 229, 231: Logs de debug
- 262-280: Tratamento de erro de validação
- 287, 289: Logs de debug
- 311-337: Tratamento de erro de fusão

**Prioridade**: Alta - impacta diretamente no endpoint multimodal

#### `src/api/routes/audio.py` (78%)
**Linhas não cobertas:**
- 122-128: Tratamento de erro de processamento
- 160-165: Tratamento de erro de transcrição
- 171-176: Tratamento de erro de análise prosódica
- 182-187: Tratamento de erro de Content Safety
- 193-198: Tratamento de erro de detecção de risco
- 302-305: Rate limiting
- 315-320: Error handling específico

**Prioridade**: Média - boa cobertura mas falta edge cases

#### `src/api/routes/video.py` (94%)
**Linhas não cobertas:**
- 255-273: Tratamento de erro de cache

**Prioridade**: Baixa - excelente cobertura

---

### 2. Utilitários

#### `src/utils/file_validation.py` (61%)
**Linhas não cobertas:**
- 50-51: Validação de magic bytes (fallback)
- 64: Log de erro
- 94-100: Validação de extensão
- 106: Log de erro
- 141-146: Validação de tamanho
- 215: Tratamento de exceção
- 231-251: Validação de MIME type
- 305-311: Validação de formato de vídeo
- 342-362: Validação de formato de áudio
- 381-424: Tratamento de erros diversos

**Prioridade**: Alta - componente de segurança

#### `src/utils/audit_logger.py` (67%)
**Linhas não cobertas:**
- 138-143: Formatação de exportação
- 161: Log de erro
- 186-210: Validação de checksum
- 214-226: Tratamento de erros
- 275-276: Rotação de logs
- 346-348: Tratamento de exceção
- 359-360: Log de erro
- 561-572: Exportação NDJSON
- 605: Log de erro
- 609-610: Tratamento de exceção
- 628-632: Verificação de integridade
- 658-701: Verificação de checksum
- 751-752: Tratamento de exceção

**Prioridade**: Média - componente de auditoria LGPD

---

## Plano de Ação

### Fase 3: User Story 1 - Unit Tests Rotas
- Cobrir linhas 121-337 de `multimodal.py` → Meta: 85%+
- Cobrir linhas 122-320 de `audio.py` → Meta: 85%+
- Cobrir linhas 255-273 de `video.py` → Meta: 95%+

### Fase 4: User Story 2 - Utils
- Cobrir linhas 50-424 de `file_validation.py` → Meta: 80%+
- Cobrir linhas 138-752 de `audit_logger.py` → Meta: 80%+

### Projeção de Cobertura Final
| Módulo | Cobertura Esperada |
|--------|-------------------|
| multimodal.py | 85% |
| audio.py | 85% |
| video.py | 95% |
| file_validation.py | 80% |
| audit_logger.py | 80% |
| **Total** | **~88-90%** |

---

## Notas

- Os módulos `video.py` já estão com boa cobertura (94%)
- `multimodal.py` precisa de atenção especial (54%)
- `file_validation.py` é crítico para segurança (61%)
- A cobertura total projetada é de ~88-90%
