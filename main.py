import os
import asyncio
import json
import configparser
import random
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ImportChatInviteRequest, GetDialogsRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.types import InputPeerChannel, Channel
from telethon.errors import UserAlreadyParticipantError


# Загрузка конфига
config = configparser.ConfigParser()
config.read('config.ini')

INVITE_LINK = config.get('SETTINGS', 'INVITE_LINK')
ONLINE_TIME = config.getint('SETTINGS', 'ONLINE_TIME')
JOIN_COUNT = config.getint('SETTINGS', 'JOIN_COUNT')
LEAVE_COUNT = config.getint('SETTINGS', 'LEAVE_COUNT')
DATA_DIR = 'data'

# Прокси (HTTP формат)
PROXY = ('http', '163.198.214.138', 8000, '9PMK4e', 'z8Bfcj')  # тип, хост, порт, логин, пароль


def load_phrases():
    phrases_file = os.path.join(DATA_DIR, 'phrases.txt')
    if not os.path.exists(phrases_file):
        print("⚠️ Файл phrases.txt не найден! Используется стандартное сообщение.")
        return ["Аккаунт активен ✅"]  # Фолбэк
    with open(phrases_file, 'r', encoding='utf-8') as f:
        phrases = [line.strip() for line in f if line.strip()]
    return phrases

PHASES_LIST = load_phrases()

class AccountManager:
    def __init__(self):
        self.joined_accounts = 0
        self.left_accounts = 0

    async def process_account(self, session_file, action):
        session_name = os.path.splitext(session_file)[0]
        json_file = os.path.join(DATA_DIR, session_file.replace('.session', '.json'))

        try:
            with open(json_file, 'r') as f:
                account_data = json.load(f)
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка загрузки JSON: {e}")
            return False

        client = TelegramClient(
            session=os.path.join(DATA_DIR, session_file),
            api_id=account_data['app_id'],
            api_hash=account_data['app_hash'],
            proxy=PROXY,
        )

        try:
            await client.connect()

            if not await client.is_user_authorized():
                print(f"[{session_name}] ❌ Не авторизован")
                return False

            # ✅ Имитация активности
            try:
                await client.get_me()
                random_phrase = random.choice(PHASES_LIST)
                await client.send_message('me', random_phrase)
            except Exception as e:
                print(f"[{session_name}] ⚠️ Ошибка имитации активности: {e}")

            me = await client.get_me()
            print(f"\n[{session_name}] 👤 @{me.username or 'без имени'}")

            if action == 'join':
                if self.joined_accounts >= JOIN_COUNT:
                    return False
                result = await self._join_channel(client, session_name)
                if result:
                    self.joined_accounts += 1
                    return True
                return False

            elif action == 'leave':
                if self.left_accounts >= LEAVE_COUNT:
                    return False
                result = await self._leave_channel(client, session_name)
                if result:
                    self.left_accounts += 1
                    return True
                return False

        except Exception as e:
            print(f"[{session_name}] ⚠️ Ошибка: {e}")
            return False
        finally:
            await client.disconnect()

    async def _join_channel(self, client, session_name):
        try:
            if 't.me/+' in INVITE_LINK:
                hash_part = extract_hash(INVITE_LINK)
                try:
                    result = await client(ImportChatInviteRequest(hash_part))
                    print(f"[{session_name}] ✅ Вступил в приватный канал: {result.chats[0].title}")
                    return True
                except Exception as e:
                    msg = str(e).lower()
                    if 'already requested' in msg or 'successfully requested' in msg:
                        print(f"[{session_name}] 🔄 Заявка уже подана/отправлена")
                        return True
                    elif 'already a participant' in msg:
                        print(f"[{session_name}] 🔁 Уже в канале")
                        return True
                    else:
                        print(f"[{session_name}] ❌ Ошибка вступления в приватный: {e}")
                        return False
            else:
                try:
                    entity = await client.get_entity(INVITE_LINK)
                    await client(JoinChannelRequest(entity))
                    print(f"[{session_name}] ✅ Вступил в публичный канал: {entity.title}")
                    return True
                except UserAlreadyParticipantError:
                    print(f"[{session_name}] 🔁 Уже в публичном канале")
                    return True
                except Exception as e:
                    print(f"[{session_name}] ❌ Ошибка вступления в публичный: {e}")
                    return False
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка при join: {e}")
            return False

    async def _leave_channel(self, client, session_name):
        try:
            channel = await get_last_joined_channel(client)
            if channel:
                await client(LeaveChannelRequest(channel))
                print(f"[{session_name}] 🚪 Вышел из: {channel.title}")
                return True
            else:
                print(f"[{session_name}] ℹ️ Нет канала для выхода")
                return False
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка выхода: {e}")
            return False


def extract_hash(link):
    if 't.me/+' in link:
        return link.split('+')[-1]
    return link


async def get_last_joined_channel(client):
    try:
        dialogs = await client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerChannel(0, 0),
            limit=50,
            hash=0
        ))

        for chat in dialogs.chats:
            if isinstance(chat, Channel):
                return chat
    except Exception as e:
        print(f"⚠️ Ошибка получения последнего канала: {e}")
    return None


def get_valid_sessions():
    return [
        f for f in os.listdir(DATA_DIR)
        if f.endswith('.session') and os.path.exists(os.path.join(DATA_DIR, f.replace('.session', '.json')))
    ]


async def main():
    print("📦 Обработка аккаунтов...")
    sessions = get_valid_sessions()

    if not sessions:
        print("❌ Нет валидных аккаунтов!")
        return

    print(f"🔢 Всего аккаунтов: {len(sessions)}")
    print(f"🎯 Канал: {INVITE_LINK}\n")

    manager = AccountManager()

    print("\n=== 🚪 ВХОД ===")
    for session in sessions:
        if manager.joined_accounts >= JOIN_COUNT:
            break
        await manager.process_account(session, 'join')

    print(f"\n⏳ Ждём {ONLINE_TIME // 60} мин...")
    await asyncio.sleep(ONLINE_TIME)

    print("\n=== 🚪 ВЫХОД ===")
    for session in sessions:
        if manager.left_accounts >= min(LEAVE_COUNT, manager.joined_accounts):
            break
        await manager.process_account(session, 'leave')

    print("\n✅ Завершено:")
    print(f"↪️ Подали заявку / вступили: {manager.joined_accounts}")
    print(f"↩️ Вышли: {manager.left_accounts}")


if __name__ == "__main__":
    asyncio.run(main())
