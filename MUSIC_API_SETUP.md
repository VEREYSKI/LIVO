# Музыка LIVO — бесплатный API

LIVO v8 использует Jamendo API для динамического поиска музыки.

## 1. Получи Client ID

Зарегистрируй приложение в Jamendo Developer Portal:
https://developer.jamendo.com/

Для быстрых тестов документация также указывает тестовый read-only Client ID `709fa152`.

## 2. Установи зависимости

```bash
python -m pip install -r requirements.txt
```

## 3. Задай Client ID

Windows PowerShell:

```powershell
$env:JAMENDO_CLIENT_ID="ТВОЙ_CLIENT_ID"
python app.py
```

Windows CMD:

```cmd
set JAMENDO_CLIENT_ID=ТВОЙ_CLIENT_ID
python app.py
```

macOS/Linux:

```bash
export JAMENDO_CLIENT_ID="ТВОЙ_CLIENT_ID"
python app.py
```

## 4. Открой

http://127.0.0.1:5000/music

Поиск выполняется через Jamendo, а результаты сохраняются в SQLite-кэш `livo_music.db` на 24 часа.

Важно: это не полный каталог коммерческих артистов вроде Drake или Travis Scott. Jamendo — отдельный каталог музыки, поэтому наличие конкретного артиста зависит от его присутствия там.
