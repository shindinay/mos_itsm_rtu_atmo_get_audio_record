#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скачивание аудио-записи разговора КЦ РТУ по номеру обращения (conversationId).

Использование:
    python scripts/get_audio_record.py <conversationId> [<conversationId> ...]
    python scripts/get_audio_record.py 188
    python scripts/get_audio_record.py 188 189

Креды берутся из .env в корне проекта (baseUrl, user_login, user_pass).
Файлы сохраняются в artifact/<conversationId>_<fileName>.

Цепочка:
    1. POST /api/Auth/login            -> accessToken
    2. GET  /api/ConversationsHistory/call-record-list?conversationId=N
       -> список записей (fileName, relativePath)
    3. GET  <baseUrl><relativePath>    -> mp3-файл
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import ssl

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJ, ".env")
OUT_DIR = os.path.join(PROJ, "artifact")

# на стенде сертификат не проходит полную проверку
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def read_env(path):
    # .env хранится в формате JSON: {"baseUrl": "...", "user_login": "...", ...}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def request(url, token=None, headers=None, data=None, method="GET"):
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as r:
        return r.read(), r.headers


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    conv_ids = sys.argv[1:]

    env = read_env(ENV_PATH)
    base = env["baseUrl"].rstrip("/")
    login = env["user_login"]
    password = env["user_pass"]

    # 1. Авторизация
    body = json.dumps({"login": login, "password": password}).encode("utf-8")
    raw, _ = request(
        base + "/api/Auth/login",
        headers={"Content-Type": "application/json"},
        data=body,
        method="POST",
    )
    token = json.loads(raw)["accessToken"]
    print("[auth] OK")

    os.makedirs(OUT_DIR, exist_ok=True)

    rc = 0
    for cid in conv_ids:
        # 2. Список записей обращения
        q = urllib.parse.urlencode({"conversationId": cid})
        url = base + "/api/ConversationsHistory/call-record-list?" + q
        try:
            raw, _ = request(url, token=token)
        except urllib.error.HTTPError as e:
            print(f"[conv {cid}] ошибка HTTP {e.code}: {e.read()[:200]}")
            rc = 1
            continue
        records = json.loads(raw)
        if not records:
            print(f"[conv {cid}] записей нет")
            continue

        # 3. Скачивание по relativePath
        for rec in records:
            rel = rec.get("relativePath") or urllib.parse.urlparse(rec.get("link", "")).path
            fname = rec.get("fileName") or rel.rsplit("/", 1)[-1]
            out = os.path.join(OUT_DIR, f"{cid}_{fname}")
            raw, _ = request(base + rel, token=token)
            with open(out, "wb") as f:
                f.write(raw)
            print(f"[conv {cid}] сохранено: {out} ({len(raw)} байт)")

    sys.exit(rc)


if __name__ == "__main__":
    main()
