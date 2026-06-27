from __future__ import annotations

import uuid


class UUIDFactory:
    def new_id(self) -> str:
        return str(uuid.uuid4())
