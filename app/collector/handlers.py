import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import Message, MessageReactionUpdated, ReactionTypeCustomEmoji, ReactionTypeEmoji

from app.db import crud
from app.db.db import get_session

router = Router()
log = logging.getLogger(__name__)

MEDIA_DIR = Path("media")


def extract_file(message: Message):
    """Возвращает (тип, file_id, имя файла) или None."""
    if message.document:
        d = message.document
        return "document", d.file_id, d.file_name or f"{d.file_unique_id}"
    if message.photo:
        p = message.photo[-1]  
        return "photo", p.file_id, f"{p.file_unique_id}.jpg"
    if message.video:
        v = message.video
        return "video", v.file_id, v.file_name or f"{v.file_unique_id}.mp4"
    if message.voice:
        return "voice", message.voice.file_id, f"{message.voice.file_unique_id}.ogg"
    if message.audio:
        a = message.audio
        return "audio", a.file_id, a.file_name or f"{a.file_unique_id}.mp3"
    return None


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def on_group_message(message: Message, bot: Bot):
    if message.from_user is None:
        return

    file_info = extract_file(message)
    file_path = None
    if file_info:
        kind, file_id, file_name = file_info
        target = MEDIA_DIR / str(message.chat.id) / f"{message.message_id}_{file_name}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            await bot.download(file_id, destination=target)
            file_path = str(target)
        except Exception as e:  
            log.warning("Не удалось скачать файл: %s", e)

    with get_session() as session:
        user = crud.get_or_create_user(
            session, message.from_user.id, message.from_user.username,
            message.from_user.first_name, message.from_user.last_name,
        )
        chat = crud.get_or_create_chat(session, message.chat.id, message.chat.title, message.chat.type)
        saved = crud.save_message(
            session, chat.id, user.id, message.message_id,
            message.text or message.caption, message.date,
            message.reply_to_message.message_id if message.reply_to_message else None,
        )
        if file_info:
            crud.add_attachment(session, saved.id, kind, file_id, file_name, file_path)

    log.info("Сохранено сообщение %s из чата %s", message.message_id, message.chat.title)


@router.message_reaction()
async def on_reaction(event: MessageReactionUpdated):
    if event.user is None:  
        return

    emojis = []
    for r in event.new_reaction:
        if isinstance(r, ReactionTypeEmoji):
            emojis.append(r.emoji)
        elif isinstance(r, ReactionTypeCustomEmoji):
            emojis.append(f"custom:{r.custom_emoji_id}")

    with get_session() as session:
        chat = crud.get_or_create_chat(session, event.chat.id, event.chat.title, event.chat.type)
        message = crud.get_message(session, chat.id, event.message_id)
        if message is None:  
            return
        user = crud.get_or_create_user(
            session, event.user.id, event.user.username,
            event.user.first_name, event.user.last_name,
        )
        crud.set_reactions(session, message.id, user.id, emojis, event.date)

    log.info("Реакции на сообщение %s: %s", event.message_id, emojis)