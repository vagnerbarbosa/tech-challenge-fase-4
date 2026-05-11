# Research: Documentação Final

## 1. Roteiro do Vídeo Demonstrativo (Demo-Video)

**Objetivo**: Provar a funcionalidade de todos os endpoints e a fusão multimodal em ~7 minutos.

**Fluxo Proposto**:
- **Intro (30s)**: Apresentação rápida do projeto "AI para Devs - Saúde da Mulher".
- **Arquitetura (1min)**: Mostrar brevemente o `architecture.md` e explicar o uso de Azure AI + YOLOv8 local.
- **Demo Texto (1min)**: 
    - Request `/analyze/text` com texto de risco (ex: "Sinto que não tenho controle da minha vida, ele me proíbe de sair").
    - Mostrar resposta com `risco_violencia: true` e sentimento negativo.
- **Demo Áudio (1min)**: 
    - Request `/analyze/audio` enviando arquivo WAV.
    - Mostrar a transcrição correta e a análise prosódica (pitch/energia).
- **Demo Vídeo (1min)**: 
    - Request `/analyze/video` enviando MP4.
    - Mostrar a detecção de instrumentos (tesoura) ou sangue via YOLOv8.
- **Demo Multimodal (2min)**: 
    - Request `/analyze/multimodal` combinando texto + áudio.
    - Explicar a ponderação de confiança e o resultado final da fusão.
- **Segurança & LGPD (30s)**: 
    - Tentar requisição sem API Key (401/403).
    - Mostrar o log de auditoria sanitizado (sem PII).
- **Conclusão (30s)**: Encerramento e link para o repositório.

**Decisão**: Gravação via OBS Studio, narração em Português, upload para YouTube como "Não listado" ou "Público".

## 2. Estrutura do API Guide

**Formato**: Seção dedicada no README + arquivos em `docs/`.

**Tópicos Obrigatórios**:
- **Autenticação**: Como obter a API Key via `/auth/api-key` e como enviá-la no header `X-API-Key`.
- **Endpoints de Análise**:
    - `/analyze/text`: Body JSON, tipos de risco detectados.
    - `/analyze/audio`: Multipart/form-data, formatos suportados (WAV, MP3, OGG).
    - `/analyze/video`: Multipart/form-data, formatos (MP4, AVI, MOV), limite de 2min.
    - `/analyze/multimodal`: Combinação de inputs e lógica de fusão.
- **Tratamento de Erros**: 
    - 400 (Bad Request), 401 (Unauthorized), 429 (Too Many Requests - Quota Azure).
- **Exemplos de Requisição**: Blocos de `curl` para cada modalidade.

**Racional**: Manter a simplicidade usando Markdown para que o guia evolua com o código.

## 3. Documentação Técnica (Deep Dive)

**Foco**: Transparência e Conformidade.

- **LGPD**: Detalhar o fluxo: `Upload` $\rightarrow$ `Hash PatientID` $\rightarrow$ `Process` $\rightarrow$ `Delete Temp File`.
- **Azure Quotas**: Explicar o `QuotaManager` (persistência em JSON/DB) e o mecanismo de "Hard Stop" para evitar cobranças.
- **Late Fusion**: Descrever a fórmula de cálculo: $Risco_{final} = \sum (Peso_{modalidade} \times Confiança_{modalidade})$.

**Alternativas Consideradas**: 
- Usar Wiki do GitHub (Rejeitado: prefere-se "Docs as Code" dentro do repo).
- Gerar PDF (Rejeitado: Markdown é mais versátil e versionável).
