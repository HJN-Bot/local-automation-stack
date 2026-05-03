# Tiny EC2 Discord Edge

This is the smallest bridge for keeping Discord online without moving the MAE/OpenClaw brain to EC2.

## Shape

```text
Discord -> EC2 edge -> Mac receiver -> Airtable pending task -> MAE orchestrator -> result polling -> Discord
```

EC2 owns only the Discord websocket, fast ack, forwarding, and result polling. Mac Mini remains the execution owner.

## Mac receiver

Run on Mac Mini:

```bash
cd /Users/jianan/Projects/local-automation-stack/mae-orchestrator
EDGE_SHARED_SECRET="change-me" venv/bin/python -m edge.mac_receiver --host 127.0.0.1 --port 18888
```

Expose it to EC2 with the narrowest tunnel you are comfortable with. Keep `/submit` and `/result` behind `Authorization: Bearer $EDGE_SHARED_SECRET`.

## EC2 edge

Install minimal dependencies on EC2:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-edge.txt
```

Run:

```bash
DISCORD_BOT_TOKEN="..." \
EDGE_SHARED_SECRET="change-me" \
EDGE_MAC_BASE_URL="https://mac-endpoint.example" \
EDGE_CHANNEL_IDS="1472614324009697412,1472614337016238303,1472614358466170930,1472614370260287561,1476944737931100221" \
venv/bin/python -m edge.ec2_discord_edge
```

## Notes

- Do not copy OpenClaw workspace or MAE state to EC2.
- Do not let EC2 become a second task database.
- Every Discord message gets an ack before waiting for Mac.
- Mac unavailable should become a Discord status message, not silence.
- Do not run EC2 edge and the Mac OpenClaw Discord gateway with the same bot token at the same time.
