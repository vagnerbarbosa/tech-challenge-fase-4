# Research: Análise de Áudio

**Feature**: 003-audio-analysis  
**Date**: 2026-04-12  
**Status**: Complete

---

## Research Topics

### 1. Azure Speech SDK Async Pattern

**Question**: Como integrar SDK síncrono do Azure Speech em aplicação FastAPI async?

**Findings**:
- Azure Speech SDK for Python é completamente síncrono (bloqueante)
- Não há suporte nativo para async/await
- Pattern recomendado: `asyncio.to_thread()` para executar em thread separada

**Decision**: Usar `asyncio.to_thread()` wrapper com timeout configurável (30s)

**Code Pattern**:
```python
result = await asyncio.wait_for(
    asyncio.to_thread(recognizer.recognize_once_async),
    timeout=30
)
```

**Rationale**: Mantém event loop não bloqueado, permite timeout controlado

---

### 2. Librosa Audio Processing

**Question**: Como extrair features prosódicas (pitch, energia, pausas) de forma eficiente?

**Findings**:
- Librosa é padrão de facto para análise de áudio em Python
- `librosa.load()` suporta múltiplos formatos via soundfile/ffmpeg
- 16kHz sampling rate é padrão para speech recognition
- `librosa.piptrack()` para pitch extraction
- `librosa.effects.split()` para detecção de silêncios

**Decision**: Usar librosa com sr=16000, mono=True

**Key Functions**:
```python
# Load audio
y, sr = librosa.load(path, sr=16000, mono=True)

# Pitch extraction
pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
pitch_values = pitches[magnitudes > threshold]
pitch_std = np.std(pitch_values) if len(pitch_values) > 0 else 0

# Energy
rms = librosa.feature.rms(y=y)[0]

# Pausas (silêncios)
intervals = librosa.effects.split(y, top_db=20)
pauses = len(intervals) - 1
```

**Rationale**: 16kHz reduz processamento vs 44.1kHz, suficiente para fala

---

### 3. Magic Numbers File Validation

**Question**: Como validar realmente o tipo de arquivo além da extensão?

**Findings**:
- Extensão pode ser spoofada facilmente
- Magic numbers (file signatures) são confiáveis
- `python-magic` é wrapper Python para libmagic (mesma do comando `file`)
- MIME types: audio/wav, audio/mpeg, audio/ogg

**Decision**: Usar python-magic para validação real, extensão apenas como hint

**Implementation**:
```python
import magic

ALLOWED_TYPES = {
    'audio/wav': '.wav',
    'audio/mpeg': '.mp3', 
    'audio/ogg': '.ogg',
    'audio/x-wav': '.wav',
}

content = await file.read(2048)  # Primeiros 2KB
mime = magic.from_buffer(content, mime=True)
if mime not in ALLOWED_TYPES:
    raise HTTPException(400, "Tipo não suportado")
```

**Rationale**: Segurança contra uploads maliciosos spoofados

---

### 4. Temp File Cleanup Strategy

**Question**: Como garantir cleanup LGPD-compliant de arquivos temporários?

**Findings**:
- `tempfile.NamedTemporaryFile` com delete=False permite controle manual
- `atexit` registra funções para execução no shutdown
- `finally` blocks garantem cleanup mesmo em exceções
- Singleton pattern permite tracking global de arquivos

**Decision**: Implementar TempFileManager singleton com três camadas de proteção

**Layers**:
1. **Explicit cleanup**: Método `cleanup()` chamado após processamento
2. **Exception cleanup**: `try/finally` em endpoint
3. **Shutdown cleanup**: `atexit.register()` para arquivos pendentes

**Code Pattern**:
```python
class TempFileManager:
    _instance = None
    _temp_files: set[Path] = set()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls._cleanup_all)
        return cls._instance
```

**Rationale**: Múltiplas camadas garantem LGPD compliance

---

### 5. Azure Speech Error Handling

**Question**: Quais erros específicos do Azure Speech precisam de tratamento?

**Findings**:
- `ResultReason.Canceled`: Cancelado (erro, timeout, etc)
- `CancellationReason.Error`: Erro interno
- `CancellationReason.EndOfStream`: Áudio vazio/inválido
- HTTP 429: Quota exceeded (precisa de retry lógica)

**Decision**: Mapear para exceções customizadas do projeto

**Error Mapping**:
| Azure Error | Exception | HTTP Status |
|-------------|-----------|-------------|
| Auth failed | AzureAuthenticationError | 503 |
| Quota exceeded | AzureQuotaExceededError | 429 |
| Timeout | TimeoutError | 504 |
| Service error | AzureServiceError | 503 |
| No speech detected | ValueError | 400 |

**Rationale**: Consistência com tratamento de erros existente no projeto

---

### 6. Prosodic Features Thresholds

**Question**: Quais thresholds usar para detecção de voz tremida e entonação?

**Findings**:
- Pitch variation (std dev) > 50 Hz indica tremor vocal
- Energy variation (std dev RMS) > 0.15 indica agitação
- Energy variation > 0.08 indica hesitação
- RMS mean < 0.05 indica fala calma/suave

**Decision**: Thresholds empíricos baseados em literatura

**Thresholds**:
```python
VOICE_TREMOR_THRESHOLD = 50.0  # Hz (pitch std)
AGITATED_THRESHOLD = 0.15      # RMS std
HESITANT_THRESHOLD = 0.08       # RMS std
CALM_MAX_MEAN = 0.05           # RMS mean
```

**Note**: Valores são heurísticos, podem precisar de ajuste com dados reais

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| SpeechRecognition (Google) | Não atende requisito Azure do projeto |
| Whisper (OpenAI) | Requer GPU, custo, fora do scope Azure |
| Vosk (offline) | Considerado como fallback, mas B foi escolhido (erro 503) |
| FFmpeg direto | Muito low-level, librosa mais Pythonic |
| In-memory processing | Não suporta arquivos grandes, streaming complexo |

---

## Open Questions

- **Fine-tuning thresholds**: Valores prosódicos precisam de validação com dataset real
- **Accent support**: Azure Speech pt-BR funciona bem com sotaques regionais brasileiros?
- **Noise handling**: Como lida com background noise em consultas reais?

---

## References

- [Azure Speech SDK Python](https://learn.microsoft.com/azure/ai-services/speech-service/quickstarts/setup-platform?pivots=programming-language-python)
- [Librosa Documentation](https://librosa.org/doc/latest/)
- [python-magic](https://github.com/ahupp/python-magic)
- [Vocal Tremor Analysis](https://www.ncbi.nlm.nih.gov/pmc/articles/PMCPMC4082302/) (literatura científica)
