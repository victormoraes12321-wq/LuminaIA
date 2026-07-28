from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from services.conversation_state.legacy_adapter import LegacyConversationImporter
from services.conversation_state.service import conversation_state_service


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import one explicit legacy conversation JSON.")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--tenant-id", type=uuid.UUID, required=True)
    parser.add_argument("--user-id", type=uuid.UUID, required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--apply", action="store_true", help="Apply import; default is dry-run.")
    args = parser.parse_args()
    result = await LegacyConversationImporter(conversation_state_service).import_file(
        path=args.path,
        tenant_id=args.tenant_id,
        user_id=args.user_id,
        public_session_id=args.session_id,
        dry_run=not args.apply,
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
