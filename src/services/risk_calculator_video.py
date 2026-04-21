"""Calculadora de risco para análise de vídeo.

Este módulo calcula níveis de risco (violência e saúde mental)
com base nas detecções do vídeo.
"""

from typing import Any


def _combine_risk_levels(risk1: str, risk2: str) -> str:
    """Combina dois níveis de risco, retornando o mais grave.

    Ordem de gravidade: alto > medio > baixo

    Args:
        risk1: Primeiro nível de risco
        risk2: Segundo nível de risco

    Returns:
        Nível de risco combinado (o mais grave)
    """
    priority = {"alto": 3, "medio": 2, "baixo": 1}
    return "alto" if priority.get(risk1, 0) >= priority.get(risk2, 0) and risk1 == "alto" else \
           "alto" if priority.get(risk2, 0) >= priority.get(risk1, 0) and risk2 == "alto" else \
           "medio" if priority.get(risk1, 0) >= priority.get(risk2, 0) and risk1 == "medio" else \
           "medio" if priority.get(risk2, 0) >= priority.get(risk1, 0) and risk2 == "medio" else \
           "baixo"


def calculate_video_risk(
    detections: list[dict[str, Any]],
    posture_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula risco baseado nas detecções do vídeo.

    Analisa as detecções de objetos, sangramento e comportamento
    para determinar níveis de risco de violência e saúde mental.

    Args:
        detections: Lista de detecções do vídeo, cada uma contendo:
            - classe: str (nome da classe detectada)
            - confianca: float (0-1)
            - bbox: dict (opcional)
            - frame: int (opcional)
            - timestamp: float (opcional)
        posture_analysis: Análise de postura opcional contendo:
            - risco_violencia: str ("baixo", "medio", "alto")
            - risco_saude_mental: str ("baixo", "medio", "alto")
            - indicadores: list[str] (indicadores de postura)
            - alertas: list[dict] (alertas de postura)

    Returns:
        Dicionário com:
            - risco_violencia: str ("baixo", "medio", "alto")
            - risco_saude_mental: str ("baixo", "medio", "alto")
            - alertas: list[dict] (alertas gerados)
    """
    risco_violencia = "baixo"
    risco_saude_mental = "baixo"
    alertas: list[dict[str, Any]] = []
    deteccoes_com_postura = detections.copy()

    # Contadores para análise
    objetos_perigosos = 0
    sangramento_detectado = False

    for det in detections:
        classe = det.get("classe", "").lower()
        confianca = det.get("confianca", 0.0)
        frame_ref = det.get("frame", 0)

        # Análise de sangramento
        if classe == "sangramento":
            if confianca > 0.8:
                risco_saude_mental = "alto"
                sangramento_detectado = True
                alertas.append({
                    "tipo": "sangramento_detectado",
                    "severidade": "alta",
                    "descricao": "Possível sangramento excessivo detectado no vídeo",
                    "frame_referencia": frame_ref,
                })
            elif confianca > 0.5 and risco_saude_mental != "alto":
                risco_saude_mental = "medio"
                sangramento_detectado = True
                alertas.append({
                    "tipo": "sangramento_detectado",
                    "severidade": "media",
                    "descricao": "Possível sangramento detectado no vídeo",
                    "frame_referencia": frame_ref,
                })

        # Análise de objetos potencialmente perigosos
        elif classe in ["scissors", "knife", "knife_blade"]:
            if confianca > 0.7:
                objetos_perigosos += 1
                if risco_violencia != "alto":
                    risco_violencia = "medio"
                alertas.append({
                    "tipo": "objeto_perigoso",
                    "severidade": "media",
                    "descricao": f"Objeto potencialmente perigoso detectado: {classe}",
                    "frame_referencia": frame_ref,
                })

        # Análise de postura (linguagem corporal)
        elif classe in ["person"]:
            # Postura defensiva ou tensa seria detectada via análise de bbox
            # Aqui apenas marcamos presença de pessoa para contexto
            pass

    # Se múltiplos objetos perigosos detectados, elevar risco
    if objetos_perigosos >= 2:
        risco_violencia = "alto"
        alertas.append({
            "tipo": "multiplos_objetos_perigosos",
            "severidade": "alta",
            "descricao": "Múltiplos objetos perigosos detectados no vídeo",
            "frame_referencia": 0,
        })

    # Sangramento excessivo sempre eleva risco de saúde para alto
    if sangramento_detectado:
        # Verificar se já não foi elevado
        pass  # Já tratado acima

    # Integrar análise de postura se fornecida
    if posture_analysis is not None:
        # Combinar risco de violência
        risco_violencia_postura = posture_analysis.get("risco_violencia", "baixo")
        risco_violencia = _combine_risk_levels(risco_violencia, risco_violencia_postura)

        # Combinar risco de saúde mental
        risco_saude_mental_postura = posture_analysis.get("risco_saude_mental", "baixo")
        risco_saude_mental = _combine_risk_levels(risco_saude_mental, risco_saude_mental_postura)

        # Adicionar alertas de postura
        alertas_postura = posture_analysis.get("alertas", [])
        for alerta in alertas_postura:
            # Marcar origem do alerta
            alerta_postura = alerta.copy()
            alerta_postura["origem"] = "postura"
            alertas.append(alerta_postura)

        # Adicionar indicadores de postura como detecções virtuais
        indicadores = posture_analysis.get("indicadores", [])
        for indicador in indicadores:
            deteccoes_com_postura.append({
                "classe": f"postura_{indicador}",
                "confianca": 0.85,
                "origem": "analise_postura",
                "tipo": "deteccao_virtual",
            })

    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "alertas": alertas,
        "deteccoes": deteccoes_com_postura,
    }
