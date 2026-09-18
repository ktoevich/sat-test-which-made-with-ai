"""Download the body of every question in the catalogue, one JSON object per line.

The bank rate-limits hard: hitting it with a dozen threads gets the whole
qbank-api host to stop answering this IP for several minutes. So this crawls
with two workers and a pause between calls, and when the host does go quiet it
waits it out rather than hammering. Reruns resume — questions already in
questions.jsonl are skipped — so an interrupted crawl just needs running again.
"""

from __future__ import annotations

import json
import queue
import random
import sys
import threading
import time
import urllib.request

from paths import API, HEADERS, LIST, QUESTIONS

WORKERS = 2
#: Seconds each worker waits between calls.
GAP = 0.45
#: How long to stand down once the host stops answering.
COOLDOWN = 420


def call(external_id: str, timeout: int = 45) -> dict:
    body = json.dumps({"external_id": external_id}).encode()
    req = urllib.request.Request(f"{API}/digital/get-question", body, HEADERS)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def wait_until_open(probe: str) -> None:
    """Block until the host answers again."""
    while True:
        try:
            call(probe, timeout=25)
            return
        except Exception as exc:
            print(f"  [blocked: {exc}] sleeping {COOLDOWN}s", flush=True)
            time.sleep(COOLDOWN)


def catalogue_ids() -> list[str]:
    """Every unique question id, in catalogue order.

    Legacy items carry an ``ibn`` instead of an ``external_id``; get-question
    takes either one in its ``external_id`` field.
    """
    ids, seen = [], set()
    for row in json.loads(LIST.read_text()):
        key = row.get("external_id") or row.get("ibn")
        if key and key not in seen:
            seen.add(key)
            ids.append(key)
    return ids


def already_done() -> set[str]:
    if not QUESTIONS.exists():
        return set()
    done = set()
    for line in QUESTIONS.open():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if "_error" not in row:
            done.add(row["_key"])
    return done


def main() -> None:
    ids = catalogue_ids()
    done = already_done()
    todo = [i for i in ids if i not in done]
    print(f"total {len(ids)} | done {len(done)} | todo {len(todo)}", flush=True)
    if not todo:
        return

    print("waiting for the host to answer...", flush=True)
    wait_until_open(todo[0])

    pending = queue.Queue()
    for i in todo:
        pending.put(i)
    write_lock = threading.Lock()
    # Only one worker sits out a block; the others idle until it comes back.
    recovery = threading.Lock()
    handle = QUESTIONS.open("a")
    count = [0]
    start = time.time()

    def worker():
        while True:
            try:
                key = pending.get_nowait()
            except queue.Empty:
                return
            row = None
            for attempt in range(6):
                try:
                    row = call(key)
                    break
                except Exception:
                    if attempt == 0:
                        time.sleep(3 + random.random() * 3)
                    elif recovery.acquire(blocking=False):
                        try:
                            wait_until_open(key)
                        finally:
                            recovery.release()
                    else:
                        while recovery.locked():
                            time.sleep(5)
            if row is None:
                row = {"_error": "gave up"}
            row["_key"] = key
            with write_lock:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                count[0] += 1
                if count[0] % 25 == 0:
                    rate = count[0] / (time.time() - start)
                    eta = (len(todo) - count[0]) / rate / 60 if rate else 0
                    print(f"  {count[0]}/{len(todo)}  {rate:.2f}/s  eta {eta:.0f}m", flush=True)
            time.sleep(GAP)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    handle.close()
    print(f"finished {count[0]}", flush=True)


if __name__ == "__main__":
    main()
