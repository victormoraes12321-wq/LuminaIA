"""
Adaptive Dashboard Engine (ADE) — Personalization Engine
---------------------------------------------------------
Aplica preferências personalizadas de usuários (ordenamento, visibilidade,
tema e tamanho de painéis) sobre o layout sem alterar o Blueprint original.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine.personalization")


class PersonalizationEngine:
    """
    Controla a customização individual da interface analítica por usuário.
    """

    def apply_preferences(
        self,
        components: List[Dict[str, Any]],
        preferences: Dict[str, Any] = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Aplica as ordenações e ocultações definidas pelo usuário.
        Retorna (lista_componentes_modificados, flag_personalizacao_aplicada).
        """
        if not preferences:
            return components, False

        modified = [c for c in components]
        applied = False

        # 1. Filtra componentes ocultos (Ocultação por usuário)
        hidden_ids = preferences.get("hidden_components", [])
        if hidden_ids:
            modified = [c for c in modified if str(c.get("id")) not in hidden_ids and c.get("name") not in hidden_ids]
            applied = True

        # 2. Reordena componentes baseando-se na ordem favorita do usuário
        order_list = preferences.get("component_order", [])
        if order_list:
            def get_order_weight(c: Dict[str, Any]) -> int:
                c_id_str = str(c.get("id"))
                c_name = c.get("name")
                
                # Se estiver na lista, o peso é seu índice de prioridade do usuário
                if c_id_str in order_list:
                    return order_list.index(c_id_str)
                if c_name in order_list:
                    return order_list.index(c_name)
                    
                # Senão, vai para o final
                return 999

            modified.sort(key=get_order_weight)
            applied = True

        # 3. Altera tema padrão do componente se houver override do usuário
        theme_override = preferences.get("theme_override")
        if theme_override:
            for c in modified:
                if "theme_config" not in c:
                    c["theme_config"] = {}
                c["theme_config"]["theme_override"] = theme_override
            applied = True

        logger.info(
            "[PersonalizationEngine] Preferências aplicadas: componentes_iniciais=%d | finais=%d | aplicado=%s",
            len(components),
            len(modified),
            applied
        )
        return modified, applied


# Export singleton
personalization_engine = PersonalizationEngine()
