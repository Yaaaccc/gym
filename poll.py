#!/usr/bin/env python3
"""定时请求虾健健门店实时状态接口,追加写入 data/history.jsonl 与 data/recent.json"""
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://xjj.cpc-api.fitron.vip/v1/user/stores/SZY00087/live-status"
DATA_DIR = "data"
HISTORY = os.path.join(DATA_DIR, "history.jsonl")
RECENT = os.path.join(DATA_DIR, "recent.json")
TZ = timezone(timedelta(hours=8))  # 北京时间
KEEP = 9000  # recent.json 最多保留条数(约 30 天,按 5 分钟一条)


def fetch(retries=3):
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                API, headers={"User-Agent": "gym-occupancy-tracker/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.load(resp)
            if payload.get("code") == 0 and isinstance(payload.get("data"), dict):
                return payload["data"]
            last_err = RuntimeError("unexpected payload: %r" % payload)
        except Exception as err:
            last_err = err
            time.sleep(10)
    raise last_err


def main():
    data = fetch()
    env = data.get("environment") or {}
    record = {
        "ts": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "count": data.get("occupancyCount"),
        "temp": env.get("temperature"),
        "humidity": env.get("humidity"),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    records = []
    if os.path.exists(RECENT):
        try:
            with open(RECENT, encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []
    records.append(record)
    records = records[-KEEP:]
    with open(RECENT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    print("recorded:", record)


if __name__ == "__main__":
    main()
