# Telegram Channel Manager

Автоматический вход и выход из Telegram каналов с использованием нескольких аккаунтов.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-репозиторий.git
cd telegram-channel-manager
```

2. Настройка констант

```bash
INVITE_LINK = https://t.me/+ваша_ссылка  ; или @username для публичных каналов
ONLINE_TIME = 300       ; Время в канале в секундах
JOIN_COUNT = 5         ; Максимальное количество входов
LEAVE_COUNT = 5        ; Максимальное количество выходов
```

### Инструкция по настройке:

1. Создайте папку `data` и поместите туда:
   - Файлы сессий (например `+1234567890.session`)
   - Соответствующие json-файлы с данными аккаунтов

2. Создайте файл `config.ini` с настройками

3. Установите зависимости из requirements.txt

```bash
pip install -r requirements.txt
```

4. Запустите скрипт

Файловая структура проекта должна выглядеть так:

```bash
telegram-channel-manager/
├── data/
│ ├── +1234567890.session
│ ├── +1234567890.json
│ └── ...
├── main.py
├── config.ini
├── requirements.txt
├── README.md
└── .gitignore
```

Для каждого аккаунта должен быть:
1. .session файл (создается при первом входе)
2. .json файл с данными (формат: {"app_id": 12345, "app_hash": "abcdef", "phone": "+1234567890"})