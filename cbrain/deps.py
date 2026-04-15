from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.engine import get_session

DBSession = Annotated[AsyncSession, Depends(get_session)]
