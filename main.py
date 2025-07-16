import os
import asyncio
import json
import configparser
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ImportChatInviteRequest, GetDialogsRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.types import InputPeerChannel, Channel, ChatInviteAlready

# Загрузка конфига
config = configparser.ConfigParser()
config.read('config.ini')

# Параметры из конфига
INVITE_LINK = config.get('SETTINGS', 'INVITE_LINK')
ONLINE_TIME = config.getint('SETTINGS', 'ONLINE_TIME')
JOIN_COUNT = config.getint('SETTINGS', 'JOIN_COUNT')
LEAVE_COUNT = config.getint('SETTINGS', 'LEAVE_COUNT')
DATA_DIR = 'data'

class AccountManager:
    def __init__(self):
        self.joined_accounts = 0
        self.left_accounts = 0

    async def process_account(self, session_file, action):
        """Обрабатывает один аккаунт для входа или выхода"""
        session_name = os.path.splitext(session_file)[0]
        json_file = os.path.join(DATA_DIR, session_file.replace('.session', '.json'))
        
        try:
            with open(json_file, 'r') as f:
                account_data = json.load(f)
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка загрузки данных: {e}")
            return False

        client = TelegramClient(
            session=os.path.join(DATA_DIR, session_file),
            api_id=account_data['app_id'],
            api_hash=account_data['app_hash']
        )

        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"[{session_name}] ❌ Аккаунт не авторизован!")
                return False

            me = await client.get_me()
            print(f"\n[{session_name}] 👤 Аккаунт: @{me.username or 'нет'} (ID: {me.id})")

            if action == 'join':
                # Проверяем лимит входа
                if self.joined_accounts >= JOIN_COUNT:
                    print(f"[{session_name}] ℹ️ Лимит входа достигнут ({JOIN_COUNT})")
                    return False
                
                # Вход в канал
                result = await self._join_channel(client, session_name)
                if result:
                    self.joined_accounts += 1
                    return True
                return False

            elif action == 'leave':
                # Проверяем лимит выхода
                if self.left_accounts >= LEAVE_COUNT:
                    print(f"[{session_name}] ℹ️ Лимит выхода достигнут ({LEAVE_COUNT})")
                    return False
                
                # Выход из канала
                result = await self._leave_channel(client, session_name)
                if result:
                    self.left_accounts += 1
                    return True
                return False

        except Exception as e:
            print(f"[{session_name}] ⚠️ Критическая ошибка: {e}")
            return False
        finally:
            await client.disconnect()
            print(f"[{session_name}] 🔌 Отключение")

    async def _join_channel(self, client, session_name):
        """Вход в канал"""
        try:
            target_entity = None
            try:
                target_entity = await client.get_entity(INVITE_LINK)
                if isinstance(target_entity, Channel):
                    print(f"[{session_name}] ℹ️ Уже состоит в канале: {target_entity.title}")
                    return True
            except:
                pass

            try:
                # Пробуем как публичный канал
                target_entity = await client.get_entity(INVITE_LINK)
                if isinstance(target_entity, Channel):
                    print(f"[{session_name}] 🌐 Публичный канал: {target_entity.title}")
                    await client(JoinChannelRequest(target_entity))
                    return True
            except:
                # Пробуем как приватный канал
                try:
                    hash_part = extract_hash(INVITE_LINK)
                    result = await client(ImportChatInviteRequest(hash=hash_part))
                    target_entity = result.chats[0]
                    print(f"[{session_name}] 🔒 Приватный канал (подана заявка): {target_entity.title}")
                    return True
                except Exception as e:
                    print(f"[{session_name}] ❌ Ошибка входа: {e}")
                    return False
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка при входе: {e}")
            return False

    async def _leave_channel(self, client, session_name):
        """Выход из канала"""
        try:
            channel_to_leave = await get_last_joined_channel(client)
            if channel_to_leave:
                await client(LeaveChannelRequest(channel_to_leave))
                print(f"[{session_name}] 🚪 Успешно вышел из канала: {channel_to_leave.title}")
                return True
            else:
                print(f"[{session_name}] ℹ️ Не найден канал для выхода")
                return False
        except Exception as e:
            print(f"[{session_name}] ❌ Ошибка выхода: {e}")
            return False

def extract_hash(invite_link):
    """Извлекает хэш из invite-ссылки"""
    if invite_link.startswith('https://t.me/+'):
        return invite_link.split('+')[-1]
    return invite_link

async def get_last_joined_channel(client):
    """Получает последний присоединенный канал"""
    result = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerChannel(0, 0),
        limit=100,
        hash=0
    ))
    
    for dialog in result.dialogs:
        if isinstance(dialog.entity, Channel):
            return dialog.entity
    return None

def get_valid_sessions():
    """Возвращает список валидных session файлов"""
    return [
        f for f in os.listdir(DATA_DIR)
        if f.endswith('.session') and 
        os.path.exists(os.path.join(DATA_DIR, f.replace('.session', '.json')))
    ]

async def main():
    print("🔍 Начинаю обработку аккаунтов...")
    sessions = get_valid_sessions()
    
    if not sessions:
        print("❌ Не найдено валидных аккаунтов в папке data!")
        return

    print(f"🔢 Всего аккаунтов: {len(sessions)}")
    print(f"🎯 Целевой канал: {INVITE_LINK}")
    print(f"⏱ Время онлайн: {ONLINE_TIME//60} минут")
    print(f"↗️ Максимум входа: {JOIN_COUNT}")
    print(f"↙️ Максимум выхода: {LEAVE_COUNT}\n")

    manager = AccountManager()

    # Фаза входа
    print("\n=== ФАЗА ВХОДА ===")
    for session in sessions:
        if manager.joined_accounts >= JOIN_COUNT:
            break
        await manager.process_account(session, 'join')

    # Ожидание
    print(f"\n⏳ Ожидание {ONLINE_TIME//60} минут...")
    await asyncio.sleep(ONLINE_TIME)

    # Фаза выхода
    print("\n=== ФАЗА ВЫХОДА ===")
    for session in sessions:
        if manager.left_accounts >= min(LEAVE_COUNT, manager.joined_accounts):
            break
        await manager.process_account(session, 'leave')

    print("\n✅ Все операции завершены!")
    print(f"↗️ Всего вошло: {manager.joined_accounts}/{JOIN_COUNT}")
    print(f"↙️ Всего вышло: {manager.left_accounts}/{min(LEAVE_COUNT, manager.joined_accounts)}")

if __name__ == "__main__":
    asyncio.run(main())