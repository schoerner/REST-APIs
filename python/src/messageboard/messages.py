from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from messageboard.errors import Error


@dataclass
class Message:
    """Entspricht dem Message-Schema in der OpenAPI-Spec."""
    id: int
    author: str
    title: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class PaginatedMessages:
    """Entspricht dem PaginatedMessages-Schema in der OpenAPI-Spec."""
    items: list[Message]
    total: int
    limit: int
    offset: int

    def to_dict(self) -> dict:
        return {
            "items": [m.to_dict() for m in self.items],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
        }


class InMemoryMessageDB:
    def __init__(
        self,
        check_author: bool = True,
        add_demo_messages: bool = True,
        max_messages: int | None = None,
    ):
        """
        check_author=True → Mutationen (PATCH, PUT, DELETE) prüfen, ob der
        anfragende Nutzer der Autor ist.
        Für authentifizierte /messages-Routen.

        check_author=False → Keine Autorenprüfung.
        Für öffentliche /public/messages-Routen.

        max_messages=None → kein Limit
        max_messages=10   → maximal 10 Nachrichten, FIFO bei Überschreitung
        """
        self.check_author = check_author
        self.max_messages = max_messages

        # dict statt list → IDs bleiben nach Deletes stabil
        self.messages: dict[int, Message] = {}
        self._next_id: int = 1

        if add_demo_messages:
            self._add_demo_messages()

    # ── interne Helpers ──────────────────────────────────────────────────────

    def _add_demo_messages(self):
        demo = [
            ("alice", "Willkommen!", "Herzlich willkommen auf dem MessageBoard.\nViel Spass beim Erkunden der API!"),
            ("bob", "REST ist toll", "HTTP-Methoden, Statuscodes, JSON - eigentlich ganz einfach."),
            ("alice", "Statuscodes", "200 OK, 201 Created, 404 Not Found, 401 Unauthorized, 403 Forbidden."),
            ("bob", "PUT vs. PATCH", "PUT ersetzt die komplette Ressource.\nPATCH aktualisiert nur angegebene Felder."),
        ]
        for author, title, content in demo:
            self._create(author=author, title=title, content=content)

    def _enforce_max_messages(self) -> None:
        """FIFO: löscht bei Überschreitung immer die älteste Nachricht."""
        if self.max_messages is None:
            return

        while len(self.messages) > self.max_messages:
            oldest_id = min(self.messages.keys())
            del self.messages[oldest_id]

    def _create(self, author: str, title: str, content: str) -> Message:
        msg = Message(
            id=self._next_id,
            author=author,
            title=title,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        self.messages[self._next_id] = msg
        self._next_id += 1

        self._enforce_max_messages()
        return msg

    def _get_or_raise(self, message_id: int) -> Message:
        msg = self.messages.get(message_id)
        if msg is None:
            raise Error.MESSAGE_NOT_FOUND(message_id)
        return msg

    # ── öffentliche API ──────────────────────────────────────────────────────

    def add_message(self, author: str, title: str, content: str) -> Message:
        """Neue Nachricht erstellen."""
        return self._create(author=author, title=title, content=content)

    def get_message(self, message_id: int) -> Message:
        """Einzelne Nachricht. Wirft 404 wenn nicht vorhanden."""
        return self._get_or_raise(message_id)

    def get_messages(self, limit: int = 20, offset: int = 0) -> PaginatedMessages:
        """Paginierte Liste aller Nachrichten, neueste zuerst."""
        all_messages = sorted(self.messages.values(), key=lambda m: m.id, reverse=True)
        return PaginatedMessages(
            items=all_messages[offset: offset + limit],
            total=len(all_messages),
            limit=limit,
            offset=offset,
        )

    def patch_message(
        self,
        message_id: int,
        author: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Message:
        msg = self._get_or_raise(message_id)

        if self.check_author and msg.author != author:
            raise Error.NOT_MESSAGE_AUTHOR()

        changed = False

        if not self.check_author:
            if author is not None and author != msg.author:
                msg.author = author
                changed = True

        if content is not None and content != msg.content:
            msg.content = content
            changed = True

        if title is not None and title != msg.title:
            msg.title = title
            changed = True

        if changed:
            msg.updated_at = datetime.now(timezone.utc)

        return msg

    def replace_message(
        self,
        message_id: int,
        author: str,
        title: str,
        content: str,
    ) -> Message:
        msg = self._get_or_raise(message_id)

        if self.check_author and msg.author != author:
            raise Error.NOT_MESSAGE_AUTHOR()

        if not self.check_author:
            msg.author = author

        msg.title = title
        msg.content = content
        msg.updated_at = datetime.now(timezone.utc)
        return msg

    def delete_message(self, message_id: int, author: str) -> None:
        msg = self._get_or_raise(message_id)

        if self.check_author and msg.author != author:
            raise Error.NOT_MESSAGE_AUTHOR()

        del self.messages[message_id]

    def reset(self) -> None:
        """Datenbank auf Demo-Daten zurücksetzen (/admin/reset)."""
        self.messages.clear()
        self._next_id = 1
        self._add_demo_messages()