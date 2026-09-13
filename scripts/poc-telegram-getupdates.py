"""One-shot PoC: can getUpdates see an inline-button tap after the process exits?

Mimics GitHub Actions: send a button, exit, then a later process polls.
Does not keep a webhook or long-poll loop across the tap.

Usage:
  set TELEGRAM_BOT_TOKEN=...
  python scripts/poc-telegram-getupdates.py send
  (tap the button in Telegram)
  python scripts/poc-telegram-getupdates.py poll
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

STATE = Path(os.environ.get("TEMP", "/tmp")) / "frost-alert-poc-telegram-state.json"
API = "https://api.telegram.org/bot{token}/{method}"


def token() -> str:
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not t:
        sys.exit("Set TELEGRAM_BOT_TOKEN to a BotFather token, then re-run.")
    return t


def call(method: str, **params):
    url = API.format(token=token(), method=method)
    data = json.dumps(params).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Telegram HTTP {e.code}: {e.read().decode()}")
    if not body.get("ok"):
        sys.exit(f"Telegram error: {body}")
    return body["result"]


def load_state() -> dict:
    if not STATE.exists():
        sys.exit("No state file. Run: python scripts/poc-telegram-getupdates.py send")
    return json.loads(STATE.read_text(encoding="utf-8"))


def cmd_send() -> None:
    me = call("getMe")
    # getUpdates is disabled while a webhook is set.
    hook = call("getWebhookInfo")
    if hook.get("url"):
        call("deleteWebhook", drop_pending_updates=False)

    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    updates = call("getUpdates", timeout=0)
    offset = 1
    if updates:
        offset = updates[-1]["update_id"] + 1
    if not chat_id:
        for u in updates:
            msg = u.get("message") or u.get("edited_message") or {}
            chat = msg.get("chat") or {}
            if chat.get("id"):
                chat_id = str(chat["id"])
                break
    if not chat_id:
        sys.exit(
            "No chat yet. Open Telegram, send /start to this bot, then re-run send.\n"
            f"Bot username: @{me.get('username', '?')}\n"
            f"Pending updates: {len(updates)}; webhook: {hook.get('url') or 'none'}"
        )

    sent = call(
        "sendMessage",
        chat_id=int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id,
        text=(
            "Frost Alert PoC: tap the button, then run "
            "`python scripts/poc-telegram-getupdates.py poll`."
        ),
        reply_markup={
            "inline_keyboard": [
                [{"text": "Plants are in overwintering", "callback_data": "ack_overwinter"}]
            ]
        },
    )
    STATE.write_text(
        json.dumps({"chat_id": chat_id, "offset": offset, "message_id": sent["message_id"]}),
        encoding="utf-8",
    )
    print(f"Sent button to chat {chat_id} as @{me.get('username')}. Tap it, then run poll.")


def cmd_poll() -> None:
    state = load_state()
    updates = call(
        "getUpdates",
        offset=state["offset"],
        timeout=0,
        allowed_updates=["callback_query"],
    )
    taps = [u for u in updates if "callback_query" in u]
    if not taps:
        print("FAIL: no callback_query. Polling did not see the tap.")
        print(f"(got {len(updates)} updates, none were button taps)")
        sys.exit(2)
    q = taps[0]["callback_query"]
    call("answerCallbackQuery", callback_query_id=q["id"], text="Ack recorded (PoC)")
    print("PASS: getUpdates received callback_query after a separate process.")
    print(f"  data={q.get('data')!r} from={q.get('from', {}).get('username')}")


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if cmd == "send":
        cmd_send()
    elif cmd == "poll":
        cmd_poll()
    else:
        sys.exit("Usage: python scripts/poc-telegram-getupdates.py {send|poll}")
