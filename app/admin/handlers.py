import csv
import io
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.db import crud
from app.db.db import get_session

router = Router()

router.message.filter(F.chat.type == "private")

ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tomsk"))

HELP = (
    "Команды администратора:\n"
    "/export ГГГГ-ММ-ДД ГГГГ-ММ-ДД — выгрузить переписку за период (включительно)\n"
    "Пример: /export 2026-11-01 2026-11-14"
)

HEADERS = ["Чат", "ID сообщения", "Дата", "ID автора", "Username", "Имя",
           "Текст", "Ответ на", "Файлы", "Реакции"]
WIDTHS = [25, 12, 20, 14, 18, 22, 60, 10, 40, 30]


def is_admin(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id in ADMIN_IDS


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=TZ)


def build_rows(messages) -> list[list]:
    rows = []
    for m in messages:
        user = m.user
        name = " ".join(filter(None, [user.first_name, user.last_name])) if user else ""
        attachments = "; ".join(
            f"{a.kind}:{a.file_name} ({a.file_path or 'не скачан'})" for a in m.attachments
        )
        reactions = "; ".join(
            f"{r.emoji} ({r.user.username or r.user.telegram_id})" for r in m.reactions
        )
        rows.append([
            m.chat.title or "", m.telegram_message_id,
            m.date.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            user.telegram_id if user else "", (user.username if user else "") or "", name,
            m.text or "", m.reply_to_message_id or "", attachments, reactions,
        ])
    return rows


def build_csv(rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(HEADERS)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def build_xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Переписка"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r, row in enumerate(rows, start=2):
        for c, value in enumerate(row, start=1):
            if isinstance(value, str):
                value = ILLEGAL_CHARACTERS_RE.sub("", value)
            cell = ws.cell(row=r, column=c, value=value)
            if isinstance(value, str):
                cell.data_type = "s"  
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for i, width in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.message(Command("start", "help"))
async def cmd_help(message: Message):
    if not is_admin(message):
        await message.answer("Нет доступа.")
        return
    await message.answer(HELP)


@router.message(Command("export"))
async def cmd_export(message: Message, command: CommandObject):
    if not is_admin(message):
        await message.answer("Нет доступа.")
        return

    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("Нужно две даты.\n\n" + HELP)
        return

    try:
        date_from = parse_date(args[0])
        date_to = parse_date(args[1]) + timedelta(days=1)  
    except ValueError:
        await message.answer("Неверный формат даты. Нужно ГГГГ-ММ-ДД, например 2026-11-14.")
        return

    if date_to <= date_from:
        await message.answer("Вторая дата не может быть раньше первой.")
        return

    with get_session() as session:
        rows = build_rows(crud.get_messages_by_period(session, date_from, date_to))

    if not rows:
        await message.answer("За этот период сообщений нет.")
        return

    name = f"export_{args[0]}_{args[1]}"
    await message.answer_document(
        BufferedInputFile(build_xlsx(rows), filename=f"{name}.xlsx"),
        caption=f"Сообщений: {len(rows)}",
    )
    await message.answer_document(
        BufferedInputFile(build_csv(rows), filename=f"{name}.csv"),
        caption="То же в формате CSV (разделитель «;», UTF-8)",
    )