#!/usr/bin/env python3
"""
Tiny EC2 Discord edge.

EC2 keeps the Discord websocket alive, immediately acknowledges messages,
then forwards work to the Mac-side MAE receiver.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import discord
import requests


MAC_BASE_URL = os.getenv("EDGE_MAC_BASE_URL", "").rstrip("/")
SHARED_SECRET = os.getenv("EDGE_SHARED_SECRET", "")
CHANNEL_IDS = {
    item.strip()
    for item in os.getenv("EDGE_CHANNEL_IDS", "").split(",")
    if item.strip()
}
POLL_INTERVAL = float(os.getenv("EDGE_POLL_INTERVAL", "8"))
RESULT_TIMEOUT = float(os.getenv("EDGE_RESULT_TIMEOUT", "900"))
TASK_TYPE = os.getenv("EDGE_DEFAULT_TASK_TYPE", "research")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SHARED_SECRET}",
        "Content-Type": "application/json",
    }


def _post_submit(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{MAC_BASE_URL}/submit",
        headers=_headers(),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _get_result(message_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{MAC_BASE_URL}/result",
        headers=_headers(),
        params={"message_id": message_id},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


async def wait_for_result(message: discord.Message, message_id: str, task_id: str) -> None:
    deadline = time.monotonic() + RESULT_TIMEOUT
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            result = await asyncio.to_thread(_get_result, message_id)
        except Exception as exc:
            await message.channel.send(f"Mac 执行端查询失败，继续重试：{type(exc).__name__}")
            continue

        status = result.get("status")
        if status == "done":
            text = result.get("result") or f"MAE task {task_id} completed."
            await message.channel.send(text[:1800])
            return
        if status == "failed":
            await message.channel.send(f"MAE task {task_id} failed: {result.get('error', 'unknown')[:1000]}")
            return

    await message.channel.send(f"MAE task {task_id} 仍在处理中，已超过 edge 等待窗口。")


class EdgeClient(discord.Client):
    async def on_ready(self) -> None:
        print(f"[discord-edge] logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or not message.content.strip():
            return
        if CHANNEL_IDS and str(message.channel.id) not in CHANNEL_IDS:
            return

        payload = {
            "message_id": str(message.id),
            "channel_id": str(message.channel.id),
            "author": str(message.author),
            "task_type": TASK_TYPE,
            "content": message.content,
        }

        try:
            accepted = await asyncio.to_thread(_post_submit, payload)
        except Exception as exc:
            await message.channel.send(f"已收到，但 Mac 执行端暂不可达：{type(exc).__name__}")
            return

        task_id = accepted.get("task_id", "unknown")
        await message.channel.send(f"收到，已转交 Mac MAE 执行。task={task_id}")
        asyncio.create_task(wait_for_result(message, str(message.id), str(task_id)))


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    if not MAC_BASE_URL:
        raise RuntimeError("EDGE_MAC_BASE_URL is required")
    if not SHARED_SECRET:
        raise RuntimeError("EDGE_SHARED_SECRET is required")

    intents = discord.Intents.default()
    intents.message_content = True
    client = EdgeClient(intents=intents)
    client.run(token)


if __name__ == "__main__":
    main()

