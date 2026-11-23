# OctagonTelegramBot

Сборщик корпоративных переписок в Telegram. Бот добавляется в рабочие чаты и сохраняет сообщения (текст, документы, фото, видео, голосовые, реакции) в PostgreSQL. Администраторы выгружают переписку за нужный период командой в личных сообщениях с ботом.

## Возможности

- Сбор сообщений из групп и супергрупп: текст, подписи, ответы на сообщения
- Сохранение вложений (документы, фото, видео, голосовые, аудио) в папку `media/`
- Сохранение реакций на сообщения
- Выгрузка переписки за период в форматах `.xlsx` и `.csv`
- Доступ к выгрузке только у администраторов из `ADMIN_IDS`

## Технологии

Python 3, aiogram 3, PostgreSQL, SQLAlchemy 2, python-dotenv, openpyxl

## Архитектура

```text
OctagonTelegramBot/
|-- app/
|   |-- main.py              # общий модуль: запуск бота, подключение модулей
|   |-- collector/
|   |   `-- handlers.py      # модуль сбора сообщений из чатов
|   |-- admin/
|   |   `-- handlers.py      # модуль интерфейса администратора (/export)
|   `-- db/
|       |-- db.py            # подключение к БД
|       |-- models.py        # описание таблиц
|       `-- crud.py          # функции работы с БД
|-- media/                   # скачанные файлы (не попадает в git)
|-- .env                     # секретные данные (не попадает в git)
|-- .gitignore
|-- requirements.txt
`-- README.md
```

Модули независимы: `collector` и `admin` работают с базой только через `db/crud.py`, а `main.py` их соединяет.

## Структура базы данных

| Таблица | Назначение | Основные поля |
|---|---|---|
| users | пользователи Telegram | telegram_id, username, first_name, last_name |
| chats | чаты | telegram_id, title, type |
| messages | сообщения | chat_id, user_id, telegram_message_id, text, date, reply_to_message_id |
| attachments | вложения | message_id, kind, file_id, file_name, file_path |
| reactions | реакции | message_id, user_id, emoji, created_at |

## Подготовка

### 1. Создание бота

1. В Telegram откройте @BotFather, выполните `/newbot` и получите токен.
2. Откройте `/mybots`, выберите бота, затем Bot Settings, Group Privacy, Turn off. Иначе бот не видит обычные сообщения в группах.
3. Добавьте бота в нужный чат и назначьте администратором. Без этого Telegram не присылает реакции.

### 2. База данных (Ubuntu / WSL)

```bash
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER octagon WITH PASSWORD '12345';"
sudo -u postgres psql -c "CREATE DATABASE tg_collector OWNER octagon;"
```

На Windows PostgreSQL устанавливается с https://www.postgresql.org/download/windows/ (вместе с pgAdmin).

### 3. Установка проекта

```bash
git clone https://github.com/loveuh4teu/OctagonTelegramBot.git
cd OctagonTelegramBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

На Windows окружение активируется командой `venv\Scripts\activate`.

### 4. Файл .env

Создайте файл `.env` в корне проекта. Он загружается командой `load_dotenv()` и не попадает в репозиторий.

| Поле | Описание | Пример |
|---|---|---|
| BOT_TOKEN | токен бота от @BotFather | PASTE_YOUR_BOT_TOKEN_HERE |
| ADMIN_IDS | числовые Telegram ID администраторов через запятую без пробелов (узнать можно у @userinfobot) | 123456789,987654321 |
| TIMEZONE | часовой пояс для разбора дат и вывода в выгрузке, необязательное, по умолчанию Asia/Tomsk | Asia/Tomsk |
| DB_HOST | адрес сервера PostgreSQL | localhost |
| DB_PORT | порт PostgreSQL | 5432 |
| DB_NAME | имя базы данных | tg_collector |
| DB_USER | пользователь PostgreSQL | octagon |
| DB_PASSWORD | пароль пользователя | REPLACE_WITH_YOUR_DB_PASSWORD |

Пример файла:

```env
BOT_TOKEN=PASTE_YOUR_BOT_TOKEN_HERE
ADMIN_IDS=123456789
TIMEZONE=Asia/Tomsk
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tg_collector
DB_USER=octagon
DB_PASSWORD=REPLACE_WITH_YOUR_DB_PASSWORD
```

## Запуск

```bash
source venv/bin/activate
python -m app.main
```

Таблицы создаются автоматически при первом запуске. В логе должна появиться строка `Start polling`. Запускать нужно из корня проекта.

## Использование

Сбор работает автоматически: пока бот запущен, все сообщения, файлы и реакции в чатах, где он состоит, сохраняются в БД.

Команды администратора доступны только в личной переписке с ботом:

| Команда | Описание |
|---|---|
| /export ГГГГ-ММ-ДД ГГГГ-ММ-ДД | выгрузка переписки за период, обе даты включительно |

Пример: `/export 2026-11-01 2026-11-14`

Бот присылает два файла: `.xlsx` и `.csv` (разделитель `;`, кодировка UTF-8). Пользователям, которых нет в `ADMIN_IDS`, бот отвечает «Нет доступа».

В выгрузке: чат, ID и дата сообщения, автор, текст, ответ на сообщение, вложения (с путём к файлу), реакции.

## Ограничения

- Бот видит только сообщения, отправленные после его добавления в чат. История до этого недоступна.
- Бот скачивает файлы размером до 20 МБ (ограничение Bot API). Для больших файлов в БД сохраняется запись без пути к файлу.
- Реакции приходят, только если бот является администратором чата.
- Сбор идёт, пока запущен процесс `python -m app.main`.

## Скриншоты и видео

Скриншоты находятся в папке `examples/`.

Видео-демонстрация: https://drive.google.com/file/d/1HRjDcIala6dymiYYDZOnlT-R5uKnBkWk/view?usp=sharing

## Дополнительная архитектурная документация
См. [ARCHITECTURE.md](ARCHITECTURE.md).

