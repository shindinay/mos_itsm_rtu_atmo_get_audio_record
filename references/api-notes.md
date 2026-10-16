# REST API КЦ РТУ (Атмосфера) — рабочие заметки

Источник: Postman-коллекция «КЦ РТУ (REST API COLLECTION)» + проверка на стенде `https://rtu-cc-01.mos.ru` (октябрь 2026).

## Авторизация

```
POST /api/Auth/login
Content-Type: application/json

{"login": "<user_login>", "password": "<user_pass>"}
```

Ответ 200: `accessToken`, `accessTokenExpires`, `refreshToken`, `refreshTokenExpires`, `userInfo{id, username, phone, ...}`.

Токен передавать в заголовке: `Authorization: Bearer <accessToken>`.
Срок жизни accessToken — около 20 минут (в тестовом ответе: 1200 с), при длинных выгрузках перезапускать скрипт или повторно логиниться.

Альтернативы из коллекции: `POST /api/Auth/token?loginId=<login>` (без тела), `POST /BearerToken/GetSysAuth` (multipart, поле `clientGuid`) — на стенде не проверялись.

## Получение записей по обращению (основной путь)

```
GET /api/ConversationsHistory/call-record-list?conversationId=<N>
```

Ответ 200 — массив (может быть пустым, если записи нет / канал не голосовой):

```json
[{
  "id": 181,
  "startTime": "2026-10-08T19:22:22+03:00",
  "disconnectTime": "2026-10-08T19:23:08+03:00",
  "duration": 45760,
  "fileName": "20261008_162222_94915__79720_E254....mp3",
  "conversationId": 188,
  "folder": "20261008",
  "srcNumber": "94915", "dstNumber": "79720",
  "calls": [],
  "link": "https://127.0.0.1:8340/call_records/...",   // нерабочий адрес
  "currentRecordingMode": "full",
  "relativePath": "/call_records/20261008/20261008_162222_....mp3"
}]
```

Скачивание:

```
GET <baseUrl><relativePath>
Authorization: Bearer <token>
```

Ответ 200, `application/octet-stream`, тело — MP3. Без токена файл не отдаётся.

## Поиск обращений (если conversationId неизвестен)

```
POST /api/ConversationsHistory/search?PerPage=20&RequestedPage=1&startDate=...&endDate=...&groupIds=...
Content-Type: application/json

{"blockContainer": [{"block": [{"selectName": "...", "propertyName": "...", "value": "...", "operation": "eq"}], "operator": "or"}], "operator": "and"}
```

Тело — фильтр-конструктор (блоки условий с операциями `eq|le|ge|like|contains`). На стенде не проверялся — при первом использовании сверить фактические `propertyName` через ответ эндпоинта (описание коллекции для них пустое).

## Список записей разговоров за период (запасной путь)

```
GET /api/CallRecords?PerPage=50&RequestedPage=1&startDate=2026-09-01T00:00:00.000Z&endDate=2026-10-16T23:59:59.000Z
```

- `startDate`/`endDate` — обязательные, иначе HTTP 400 «The startDate field is required.»
- Формат ISO 8601 с Z (UTC).
- Ответ: `{perPage, lastPage, currentPage, total, data: [...]}`.

Элемент `data`:

```json
{
  "id": 181,
  "startTime": "2026-10-08T19:22:22+03:00",
  "disconnectTime": "2026-10-08T19:23:08+03:00",
  "duration": 45760,
  "srcNumber": "94915", "dstNumber": "79720",
  "link": "https://127.0.0.1:8340/call_records/...",
  "direction": "Входящий",
  "ownerId": 188,              // == conversationId
  "ownerType": "conversation",
  "ownerName": "188",
  "isRotated": false
}
```

Поля `link` нет в Query-параметрах, есть опциональные `SearchText`, `Direction`, `Property`, `ownerIds`, `ownerType`.

## Известные проблемы стенда

- `GET /api/ConversationProcessing/call-record?conversationId=N` → HTTP 500, `System.ArgumentNullException` в `AutoMapping.cs` (серверный баг маппинга, RTU 2.2.0). Не использовать.
- Поле `link` всегда указывает на `127.0.0.1:8340` — собирать URL из `relativePath` (или `folder` + `fileName`).
- TLS-сертификат стенда не проходит полную проверку (отсутствие в доверенных) — отключать верификацию.
