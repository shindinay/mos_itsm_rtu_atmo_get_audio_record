#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скачивание аудио-записей разговоров КЦ РТУ (Атмосфера) по conversationId.

Использование:
    python get_audio_record.py <conversationId> [<conversationId> ...] [--env PATH] [--out DIR]

Примеры:
    python get_audio_record.py 188
    python get_audio_record.py 188 189 --out artifact

Цепочка: POST /api/Auth/login -> GET /api/ConversationsHistory/call-record-list?conversationId=N
         -> GET <baseUrl><relativePath> (mp3).
Креды берутся из .env (формат JSON: baseUrl, user_login, user_pass).
По умолчанию .env ищется в текущей папке, затем рядом со скриптом; файлы сохраняются в ./artifact.
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# сертификат стенда не проходит полную проверку
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def find_env(explicit):
    candidates = [explicit, os.path.join(os.getcwd(), ".env"), os.path.join(SCRIPT_ROOT, ".env")]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    print("Не найден .env (формат JSON: baseUrl, user_login, user_pass). "
          "Укажите путь через --env.", file=sys.stderr)
    sys.exit(1)


def request(url, token=None, headers=None, data=None, method="GET"):
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(description="Скачивание аудио-записей КЦ РТУ по conversationId")
    ap.add_argument("conversation_ids", nargs="+", help="номера обращений (conversationId)")
    ap.add_argument("--env", default=None, help="путь к .env (формат JSON)")
    ap.add_argument("--out", default=None, help="папка для файлов (по умолчанию ./artifact)")
    args = ap.parse_args()

    env = json.load(open(find_env(args.env), encoding="utf-8"))
    base = env["baseUrl"].rstrip("/")
    login = env["user_login"]
    password = env["user_pass"]
    out_dir = args.out or os.path.join(os.getcwd(), "artifact")

    body = json.dumps({"login": login, "password": password}).encode("utf-8")
    raw = request(
        base + "/api/Auth/login",
        headers={"Content-Type": "application/json"},
        data=body,
        method="POST",
    )
    token = json.loads(raw)["accessToken"]
    print("[auth] OK")

    os.makedirs(out_dir, exist_ok=True)

    rc = 0
    for cid in args.conversation_ids:
        q = urllib.parse.urlencode({"conversationId": cid})
        try:
            records = json.loads(request(base + "/api/ConversationsHistory/call-record-list?" + q, token=token))
        except urllib.error.HTTPError as e:
            print(f"[conv {cid}] ошибка HTTP {e.code}: {e.read()[:200]}")
            rc = 1
            continue
        if not records:
            print(f"[conv {cid}] записей нет")
            continue

        for rec in records:
            rel = rec.get("relativePath") or urllib.parse.urlparse(rec.get("link", "")).path
            fname = rec.get("fileName") or rel.rsplit("/", 1)[-1]
            out = os.path.join(out_dir, f"{cid}_{fname}")
            raw = request(base + rel, token=token)
            with open(out, "wb") as f:
                f.write(raw)
            print(f"[conv {cid}] сохранено: {out} ({len(raw)} байт)")

    sys.exit(rc)


if __name__ == "__main__":
    main()
