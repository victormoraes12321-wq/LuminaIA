"""
Dataset Builder — LuminaAI Data Platform
---------------------------------------
Normaliza e transforma resultados brutos ou intermediários de consultas da
Data Platform em um formato de Dataset consistente e portável.
"""
import uuid
import logging
import hashlib
from datetime import datetime, timezone, date, time
from typing import Any

logger = logging.getLogger("luminaai.data_platform.dataset_builder")


class DatasetBuilder:
    """
    Formatador estrutural de Datasets.
    """

    def build_dataset(
        self,
        tenant_id: uuid.UUID,
        raw_rows: list[dict[str, Any]],
        view_name: str,
        version: int = 1,
        metadados_adicionais: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Constrói o dicionário de Dataset padronizado.
        """
        logger.debug("[DatasetBuilder] Construindo dataset para view %s", view_name)
        
        # 1. Determina tipos das colunas
        col_types = {}
        if raw_rows:
            first = raw_rows[0]
            for col_name, val in first.items():
                if isinstance(val, bool):
                    col_types[col_name] = "boolean"
                elif isinstance(val, int):
                    col_types[col_name] = "integer"
                elif isinstance(val, float):
                    col_types[col_name] = "float"
                elif isinstance(val, (datetime, date, time)):
                    col_types[col_name] = "date"
                else:
                    col_types[col_name] = "string"

        # 2. Higieniza dados para formato JSON seguro
        safe_rows = []
        for r in raw_rows:
            safe_r = {}
            for k, v in r.items():
                if isinstance(v, (datetime, date, time)):
                    safe_r[k] = v.isoformat()
                else:
                    safe_r[k] = v
            safe_rows.append(safe_r)

        # 3. Calcula Checksum/Hash
        data_str = str(safe_rows)
        checksum = hashlib.md5(data_str.encode("utf-8")).hexdigest()

        meta = {
            "view_name": view_name,
            "origem": "DATA_PLATFORM",
            "quantidade_registros": len(safe_rows),
            "colunas": list(col_types.keys()),
            "checksum": checksum,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": str(tenant_id),
            "versao": version,
        }
        
        if metadados_adicionais:
            meta.update(metadados_adicionais)

        return {
            "metadata": meta,
            "schema": col_types,
            "data": safe_rows
        }


# Singleton export
dataset_builder = DatasetBuilder()
