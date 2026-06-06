from collections import defaultdict
from datetime import datetime, timedelta

from core.config import settings
from core.logger import logger


class SessionMemory:

    def __init__(self):
        self.sessions = defaultdict(list)
        self.expiry = {}

    def _cleanup_expired(self):

        now = datetime.utcnow()

        expired = [
            sid
            for sid, expiry in (
                self.expiry.items()
            )
            if expiry < now
        ]

        for sid in expired:
            logger.info(
                f"Cleaning expired session: {sid}"
            )
            del self.sessions[sid]
            del self.expiry[sid]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ):

        self._cleanup_expired()

        self.sessions[
            session_id
        ].append(
            {
                "role": role,
                "content": content
            }
        )

        self.expiry[
            session_id
        ] = (
            datetime.utcnow()
            + timedelta(
                minutes=settings.SESSION_TTL_MINUTES
            )
        )

        logger.info(
            f"Message added to session: "
            f"{session_id}"
        )

    def get_recent_history(
        self,
        session_id: str
    ):

        self._cleanup_expired()
        history = self.sessions.get(
            session_id,
            []
        )
        return history[
            -settings.MEMORY_WINDOW_SIZE:
        ]


session_memory = SessionMemory()