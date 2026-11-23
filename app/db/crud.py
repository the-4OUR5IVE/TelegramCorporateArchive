from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Attachment, Chat, Message, Reaction, User


def get_or_create_user(session: Session, telegram_id: int, username=None,
                       first_name=None, last_name=None) -> User:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
    
    user.username, user.first_name, user.last_name = username, first_name, last_name
    session.commit()
    return user


def get_or_create_chat(session: Session, telegram_id: int, title: Optional[str], chat_type: str) -> Chat:
    chat = session.scalar(select(Chat).where(Chat.telegram_id == telegram_id))
    if chat is None:
        chat = Chat(telegram_id=telegram_id)
        session.add(chat)
    chat.title, chat.type = title, chat_type
    session.commit()
    return chat


def get_message(session: Session, chat_id: int, telegram_message_id: int) -> Optional[Message]:
    return session.scalar(
        select(Message).where(
            Message.chat_id == chat_id,
            Message.telegram_message_id == telegram_message_id,
        )
    )


def save_message(session: Session, chat_id: int, user_id: Optional[int], telegram_message_id: int,
                 text: Optional[str], date: datetime, reply_to_message_id: Optional[int]) -> Message:
    message = get_message(session, chat_id, telegram_message_id)
    if message is not None:  
        return message
    message = Message(
        chat_id=chat_id, user_id=user_id, telegram_message_id=telegram_message_id,
        text=text, date=date, reply_to_message_id=reply_to_message_id,
    )
    session.add(message)
    session.commit()
    return message


def add_attachment(session: Session, message_id: int, kind: str, file_id: str,
                   file_name: Optional[str], file_path: Optional[str]) -> Attachment:
    attachment = Attachment(message_id=message_id, kind=kind, file_id=file_id,
                            file_name=file_name, file_path=file_path)
    session.add(attachment)
    session.commit()
    return attachment


def set_reactions(session: Session, message_id: int, user_id: int,
                  emojis: list[str], date: datetime) -> None:

    session.execute(
        delete(Reaction).where(Reaction.message_id == message_id, Reaction.user_id == user_id)
    )
    for emoji in set(emojis):
        session.add(Reaction(message_id=message_id, user_id=user_id, emoji=emoji, created_at=date))
    session.commit()


def get_messages_by_period(session: Session, date_from: datetime, date_to: datetime,
                           chat_telegram_id: Optional[int] = None) -> list[Message]:
    
    stmt = (
        select(Message)
        .options(
            selectinload(Message.user), selectinload(Message.chat),
            selectinload(Message.attachments), selectinload(Message.reactions).selectinload(Reaction.user),
        )
        .where(Message.date >= date_from, Message.date < date_to)
        .order_by(Message.date)
    )
    if chat_telegram_id is not None:
        stmt = stmt.join(Chat).where(Chat.telegram_id == chat_telegram_id)
    return list(session.scalars(stmt))