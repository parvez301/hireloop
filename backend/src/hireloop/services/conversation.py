"""Conversation + Message CRUD, scoped by user_id."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.conversation import Conversation, Message


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: UUID, title: str | None = None) -> Conversation:
        row = Conversation(user_id=user_id, title=title)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_user(self, user_id: UUID, *, limit: int = 20) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def delete(self, user_id: UUID, conversation_id: UUID) -> bool:
        conv = await self.get(user_id, conversation_id)
        if conv is None:
            return False
        await self.session.delete(conv)
        await self.session.flush()
        return True

    async def list_messages(self, conversation_id: UUID, *, limit: int = 50) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_placeholder_assistant_message(self, conversation_id: UUID) -> Message:
        row = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="",
            meta_={"status": "running"},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def touch(self, conversation_id: UUID) -> None:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await self.session.execute(stmt)).scalar_one_or_none()
        if conv is None:
            return
        conv.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def auto_title_from_first_message(
        self, conversation_id: UUID, user_message_text: str
    ) -> None:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await self.session.execute(stmt)).scalar_one_or_none()
        if conv is None or conv.title:
            return
        conv.title = user_message_text.strip()[:50] or "Untitled"
        await self.session.flush()
