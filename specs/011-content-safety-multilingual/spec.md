# Feature Specification: Content Safety Multilingual

**Feature Branch**: `[011-content-safety-multilingual]`  
**Created**: 2026-05-01  
**Updated**: 2026-05-01  
**Status**: ✅ COMPLETED  
**Input**: User description: "Adicionar suporte ao Azure AI Content Safety para detecção multilíngue de risco"

---

## Clarifications

### Session 2026-05-01
- **Q**: Por que adicionar Content Safety se já temos palavras-chave?  
  **A**: Palavras-chave são limitadas a PT/EN e requerem manutenção manual. Content Safety oferece detecção ML-based em 100+ idiomas automaticamente.
- **Q**: Qual a estratégia de fallback quando Content Safety falha?  
  **A**: Keywords em PT/EN são sempre usadas como complemento/fallback, garantindo que risco seja detectado mesmo sem Content Safety.
- **Q**: Como integrar com o detector de risco existente?  
  **A**: Criar `MultilingualRiskDetector` que combina Content Safety + keywords, priorizando o máximo entre ambos.

---

## User Scenarios & Testing

### User Story 1 - Detecção Multilíngue de Risco (Priority: P1) ✅ COMPLETED

Como operador de saúde, quero detectar risco de violência e saúde mental em qualquer idioma para atender mulheres de diversas nacionalidades.

**Why this priority**: Mulheres imigrantes ou em situação de refúgio podem se expressar em idiomas diferentes do português.

**Independent Test**: Texto em espanhol, árabe ou francês é corretamente analisado para risco.

**Acceptance Scenarios**:

1. **Given** texto em espanhol com indicação de risco, **When** analiso, **Then** Content Safety detecta severidade elevada ✅
2. **Given** texto em português, **When** analiso, **Then** Content Safety ou keywords detectam risco ✅
3. **Given** texto em inglês, **When** analiso, **Then** ambos detectam risco combinado ✅
4. **Given** texto neutro em qualquer idioma, **When** analiso, **Then** risco é baixo/nenhum ✅

### User Story 2 - Fallback Robusto (Priority: P1) ✅ COMPLETED

Como desenvolvedor, quero garantir que a detecção de risco funcione mesmo se Content Safety falhar.

**Why this priority**: Azure Content Safety tem quotas e pode estar indisível; sistema não pode parar.

**Independent Test**: Desabilitar Content Safety e verificar que keywords ainda funcionam.

**Acceptance Scenarios**:

1. **Given** Content Safety desabilitado, **When** analiso texto, **Then** keywords detectam risco ✅
2. **Given** Content Safety habilitado mas falha, **When** analiso texto, **Then** fallback para keywords ✅
3. **Given** Content Safety funciona, **When** analiso texto, **Then** usa o máximo entre CS e keywords ✅

### User Story 3 - Categorias de Risco (Priority: P2) ✅ COMPLETED

Como analista, quero entender qual tipo de risco foi detectado (autoagressão, violência, ódio, sexual).

**Why this priority**: Diferentes categorias requerem diferentes protocolos de resposta.

**Independent Test**: Verificar que severidade por categoria é retornada corretamente.

**Acceptance Scenarios**:

1. **Given** texto com ideias suicidas, **When** analiso, **Then** SelfHarm tem severidade alta ✅
2. **Given** texto com ameaça física, **When** analiso, **Then** Violence tem severidade alta ✅
3. **Given** texto seguro, **When** analiso, **Then** todas as categorias têm severidade baixa ✅

---

## Requirements

### Functional Requirements ✅ ALL COMPLETED

- **FR-001**: Integração com Azure AI Content Safety API ✅
- **FR-002**: Detecção de 4 categorias: SelfHarm, Violence, Hate, Sexual ✅
- **FR-003**: Suporte a 100+ idiomas automaticamente ✅
- **FR-004**: Fallback para keywords PT/EN quando CS indisponível ✅
- **FR-005**: Combinação de scores (máximo entre CS e keywords) ✅
- **FR-006**: Mock server para Content Safety em desenvolvimento ✅
- **FR-007**: Configuração via variáveis de ambiente ✅
- **FR-008**: Validação de credenciais na inicialização ✅

### Key Entities

- **ContentSafetyClient**: Cliente para Azure AI Content Safety API
- **ContentSafetyResult**: Resultado com severidades por categoria (0-6)
- **MultilingualRiskDetector**: Serviço combinado CS + Keywords
- **RiskAssessmentResult**: Resultado final com risco calculado
- **Mock Content Safety**: Servidor mock na porta 3004

---

## Success Criteria ✅ ALL ACHIEVED

- **SC-001**: Detecção de risco funciona em múltiplos idiomas ✅
- **SC-002**: Sistema funciona mesmo sem Content Safety (fallback) ✅
- **SC-003**: Severidade retornada em escala 0-6 por categoria ✅
- **SC-004**: Mock server disponível para desenvolvimento ✅
- **SC-005**: Testes unitários cobrem CS client e detector ✅
- **SC-006**: Configuração via env vars documentada ✅

---

## Implementation Summary

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                  MultilingualRiskDetector                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Content Safety (Azure AI) - Quando disponível     │   │
│  │  • SelfHarm: 0-6                                   │   │
│  │  • Violence: 0-6                                   │   │
│  │  • Hate: 0-6                                       │   │
│  │  • Sexual: 0-6                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↕                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Keywords (PT/EN) - Sempre ativo                   │   │
│  │  • violencia / violence                            │   │
│  │  • saude_mental / mental_health                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Combined Result (max(CS, keywords))                │   │
│  │  • overall_risk: 0.0-1.0                            │   │
│  │  • risk_level: none/low/medium/high/critical        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Files Created/Modified

**Cliente Content Safety:**
- `src/infrastructure/content_safety_client.py` - Cliente Azure Content Safety

**Serviço de Detecção:**
- `src/services/multilingual_risk_detector.py` - Detector combinado CS + Keywords

**Mock Server:**
- `mock/azure/main.py` - Adicionado endpoint Content Safety na porta 3004

**Configuração:**
- `src/core/config.py` - Adicionadas variáveis Content Safety

**Testes Unitários:**
- `tests/unit/infrastructure/test_content_safety_client.py` - Testes do cliente
- `tests/unit/services/test_multilingual_risk_detector.py` - Testes do detector

**Docker Compose:**
- `docker-compose.yml` - Env vars Content Safety
- `docker-compose.mock.yml` - Mock server na porta 3004
- `docker-compose.prod.yml` - Env vars para produção

**Environment:**
- `.env.example` - Documentação das variáveis

---

## Technical Notes

### Azure AI Content Safety

**Categorias Detectadas:**
| Categoria | Descrição | Severidade |
|-----------|-----------|------------|
| SelfHarm | Autoagressão, suicídio | 0-6 |
| Violence | Violência física, ameaças | 0-6 |
| Hate | Discurso de ódio | 0-6 |
| Sexual | Conteúdo sexual inapropriado | 0-6 |

**Escala de Severidade:**
- 0: Nenhum conteúdo detectado
- 2: Baixo
- 4: Médio
- 6: Alto

### Configuração de Variáveis de Ambiente

```bash
# Habilitar Content Safety
CONTENT_SAFETY_ENABLED=true

# Credenciais Azure
AZURE_CONTENT_SAFETY_KEY=your_key_here
AZURE_CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
```

### Mock Server (Desenvolvimento)

O mock server simula o Content Safety baseado em palavras-chave:
- Porta 3004: Content Safety
- Lógica: Contagem de keywords → severidade 0-6
- Keywords suportadas: PT/EN para self-harm, violence, hate, sexual

### Padrão de Uso

```python
from src.services.multilingual_risk_detector import get_risk_detector

# Obtém detector singleton
detector = get_risk_detector()

# Analisa texto
result = detector.analyze_text("Estou me sentindo muito ansiosa")

# Resultado
print(result.overall_risk)      # 0.0-1.0
print(result.risk_level)        # none/low/medium/high/critical
print(result.to_dict())         # Dicionário completo
```

### Tratamento de Erros

- **QuotaExceededError (429)**: Log warning, fallback para keywords
- **AuthenticationError (401/403)**: Log error, fallback para keywords
- **ConnectionError**: Log error, fallback para keywords
- **AzureConfigurationError**: Falha na inicialização se credenciais inválidas

### Benefícios do Content Safety

1. **100+ Idiomas**: Detecção automática sem configuração
2. **ML-Based**: Modelos treinados com dados reais
3. **Escalável**: Gerenciado pela Azure, não consome recursos locais
4. **Atualizado**: Modelos melhorados continuamente pela Microsoft
5. **Severidade Granular**: Escala 0-6 permite ações diferenciadas

### Limitações Conhecidas

1. **Quota**: Azure Free Tier tem limites
2. **Latência**: Requisição HTTP adicional (~100-300ms)
3. **Custo**: Cobrança por requisição em alta escala
4. **Dependência**: Requer conectividade com Azure

---

## Testes

### Testes Unitários - Content Safety Client

```bash
poetry run pytest tests/unit/infrastructure/test_content_safety_client.py -v
```

Cobertura:
- Inicialização com credenciais
- Análise de texto
- Tratamento de erros (quota, auth, connection)
- Parse de resposta
- Batch analysis
- Singleton pattern

### Testes Unitários - Multilingual Risk Detector

```bash
poetry run pytest tests/unit/services/test_multilingual_risk_detector.py -v
```

Cobertura:
- Inicialização com/sem Content Safety
- Detecção com Content Safety
- Detecção com keywords apenas
- Detecção multilíngue (PT/EN)
- Fallback quando CS falha
- Cálculo combinado de risco
- Batch analysis
- Níveis de risco (none/low/medium/high/critical)

---

## Provisionamento

O Azure AI Content Safety é provisionado **automaticamente junto com os outros serviços cognitivos** (Text, Speech, Vision). Não requer passos adicionais manuais.

### Scripts de Provisionamento

**check-azure.sh** - Deploy manual:
```bash
./scripts/check-azure.sh deploy
# Cria: Text, Speech, Vision, Content Safety
```

**deploy-azure.yml** - CI/CD Pipeline:
- Trigger em push para main
- Cria todos os serviços cognitivos automaticamente
- Configura variáveis de ambiente no container

### Recursos Criados

| Recurso | Tipo | SKU |
|---------|------|-----|
| tech-challenge-text | TextAnalytics | F0 (Free) |
| tech-challenge-speech | SpeechServices | F0 (Free) |
| tech-challenge-vision | ComputerVision | F0 (Free) |
| **tech-challenge-content-safety** | **ContentSafety** | **F0 (Free)** |

### Variáveis Configuradas Automaticamente

- `AZURE_CONTENT_SAFETY_ENDPOINT`
- `AZURE_CONTENT_SAFETY_KEY`
- `CONTENT_SAFETY_ENABLED=true`

---

## Changelog

### 2026-05-01 - Implementação Concluída
- ✅ ContentSafetyClient implementado
- ✅ MultilingualRiskDetector implementado
- ✅ Mock server Content Safety na porta 3004
- ✅ Testes unitários completos
- ✅ Configuração via env vars
- ✅ Integração com sistema existente
- ✅ Provisionamento integrado aos scripts existentes

---

## Referências

- Documentação Azure AI Content Safety: https://learn.microsoft.com/azure/ai-services/content-safety/
- API Reference: https://learn.microsoft.com/azure/ai-services/content-safety/reference-rest-api
- Best Practices: https://learn.microsoft.com/azure/ai-services/content-safety/concepts/safety-practices
