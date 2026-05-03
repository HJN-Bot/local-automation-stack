import requests
import json
import os
from functools import lru_cache


def _get_token(app_id: str, app_secret: str) -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    return resp.json()["tenant_access_token"]


def _pm_token() -> str:
    return _get_token(
        os.getenv("FEISHU_PM_APP_ID"),
        os.getenv("FEISHU_PM_APP_SECRET"),
    )


def _worker_token() -> str:
    return _get_token(
        os.getenv("FEISHU_WORKER_APP_ID"),
        os.getenv("FEISHU_WORKER_APP_SECRET"),
    )


def _coder_token() -> str:
    return _get_token(
        os.getenv("FEISHU_CODER_APP_ID"),
        os.getenv("FEISHU_CODER_APP_SECRET"),
    )


def _token_for(bot_name: str) -> str:
    if bot_name == "MAE-PM":
        return _pm_token()
    if bot_name == "MAE-Coder":
        return _coder_token()
    return _worker_token()  # DS-Worker 默认


def send_message(chat_id: str, text: str, bot_name: str = "MAE-PM") -> str:
    """发送消息到群，返回 message_id"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": f"Bearer {_token_for(bot_name)}"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["message_id"]


def reply_message(message_id: str, text: str, bot_name: str = "MAE-PM") -> str:
    """回复某条消息（形成线程）"""
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
        headers={"Authorization": f"Bearer {_token_for(bot_name)}"},
        json={
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["message_id"]
