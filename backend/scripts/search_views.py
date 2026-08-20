import os
import re

backend_dir = r"C:\LuminaAI\backend"
matches = []

for root, dirs, files in os.walk(backend_dir):
    for f in files:
        if f.endswith('.py') or f.endswith('.env') or f.endswith('.sql'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    for idx, line in enumerate(fh, 1):
                        if 'vw_vendas' in line.lower() or 'vendas_lm' in line.lower() or 'clone' in line.lower() or 'analytical' in line.lower():
                            if len(matches) < 30:
                                matches.append(f"{p}:{idx}: {line.strip()[:100]}")
            except Exception:
                pass

for m in matches:
    print(m)
