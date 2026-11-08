#!/usr/bin/env python3
"""定时请求虾健健门店实时状态接口。

GitHub Actions 定时器最快只能 5 分钟一次,所以每次任务内连续记录多条:
- data/history.jsonl:全量追加(约每 30 秒一条),唯一的完整档案
- data/recent.json:网页用,**每次运行都从 history.jsonl 重新生成**(幂等):
  今天保留全量,更早的按 5 分钟抽稀,最多保留 KEEP_DAYS 天
"""
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
TICKS = 8          # 每次任务连续记录的条数(约 4 分钟)
INTERVAL = 30      # 两条记录之间的间隔(秒)
KEEP_DAYS = 30     # recent.json 保留天数


def fetch_once(timeout=15, retries=2):
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(
                API, headers={"User-Agent": "gym-occupancy-tracker/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
            if payload.get("code") == 0 and isinstance(payload.get("data"), dict):
                return payload["data"]
            last_err = RuntimeError("unexpected payload: %r" % payload)
        except Exception as err:
            last_err = err
            time.sleep(5)
    print("fetch failed: %r" % last_err)
    return None


def to_record(data):
    env = data.get("environment") or {}
    return {
        "ts": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "count": data.get("occupancyCount"),
        "temp": env.get("temperature"),
        "humidity": env.get("humidity"),
    }


def build_recent():
    """从 history.jsonl 重建 recent.json 内容(幂等:结果只取决于档案)。"""
    now = datetime.now(TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = today_start - timedelta(days=KEEP_DAYS - 1)
    dedup = {}
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("ts") and r.get("count") is not None:
                    dedup[r["ts"]] = r
    kept = []
    for ts in sorted(dedup):
        dt = datetime.fromisoformat(ts)
        if dt >= today_start:
            kept.append(dedup[ts])                 # 今天:全量(30 秒粒度)
        elif dt >= cutoff and dt.minute % 5 == 0:  # 更早:按 5 分钟网格抽稀
            kept.append(dedup[ts])
    return kept


def main():
    new = []
    for i in range(TICKS):
        tick_start = time.monotonic()
        data = fetch_once()
        if data:
            new.append(to_record(data))
        if i < TICKS - 1:
            pause = INTERVAL - (time.monotonic() - tick_start)
            time.sleep(max(0, pause))
    if not new:
        raise SystemExit("所有请求都失败,本次不写入")

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        for r in new:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    records = build_recent()
    with open(RECENT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    print("recorded %d, recent total %d, last:" % (len(new), len(records)), new[-1])


if __name__ == "__main__":
    main()
