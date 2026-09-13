#!/usr/bin/env python3
"""승선생활관 생활교육지도관 공지를 확인하고 ntfy로 푸시합니다."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SEEN_PATH = DATA_DIR / "seen.json"
LOG_PATH = DATA_DIR / "watcher.log"
ENV_PATH = ROOT / ".env"

NOTICE_LIST_URL = (
    "https://www.kmou.ac.kr/badaro/na/ntt/selectNttList.do"
    "?mi=4370&bbsId=10003004"
)
WARMUP_URL = "https://www.kmou.ac.kr/badaro/main.do"
SITE_ORIGIN = "https://www.kmou.ac.kr"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

NTT_SN_RE = re.compile(r"nttSn=(\d+)")
DATE_RE = re.compile(r"\d{4}[.\-]\d{1,2}[.\-]\d{1,2}")


@dataclass(frozen=True)
class Notice:
    ntt_sn: str
    title: str
    url: str
    date: str = ""
    author: str = ""


def setup_logging() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists() and LOG_PATH.stat().st_size > 1_000_000:
        old = LOG_PATH.with_suffix(".log.old")
        old.unlink(missing_ok=True)
        LOG_PATH.replace(old)

    handlers: list[logging.Handler] = [
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ]
    using_pythonw = Path(sys.executable).name.lower() == "pythonw.exe"
    if sys.stdout and not using_pythonw:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(env: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key, env.get(key, default)).strip()


def ensure_topic(env: dict[str, str]) -> str:
    topic = env_value(env, "NTFY_TOPIC")
    if topic and topic not in {"여기에-나만의-토픽", "change-me"}:
        return topic

    topic = f"kmou-seungsun-{random.randrange(100000, 999999)}"
    lines: list[str] = []
    replaced = False
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if raw.startswith("NTFY_TOPIC="):
                lines.append(f"NTFY_TOPIC={topic}")
                replaced = True
            else:
                lines.append(raw)
    if not replaced:
        lines.append(f"NTFY_TOPIC={topic}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.info("NTFY_TOPIC이 없어 새로 만들었습니다: %s", topic)
    return topic


def normalize_notice_url(href: str) -> str:
    absolute = urljoin(SITE_ORIGIN, href)
    parts = urlsplit(absolute)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "currPage"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def parse_notices(html: str) -> list[Notice]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, Notice] = {}

    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        match = NTT_SN_RE.search(href)
        if not match:
            continue
        if "selectNttInfo" not in href and "nttSn=" not in href:
            continue

        ntt_sn = match.group(1)
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title:
            continue

        date = ""
        author = ""
        row = anchor.find_parent("tr")
        if row:
            cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            for cell in cells:
                if DATE_RE.fullmatch(cell.replace(" ", "")):
                    date = cell
            # 번호, 제목, 작성자, 등록일, 조회 순서를 우선 사용합니다.
            if len(cells) >= 4:
                author = cells[2]

        found[ntt_sn] = Notice(
            ntt_sn=ntt_sn,
            title=title,
            url=normalize_notice_url(href),
            date=date,
            author=author,
        )

    if not found:
        for match in NTT_SN_RE.finditer(html):
            ntt_sn = match.group(1)
            found.setdefault(
                ntt_sn,
                Notice(
                    ntt_sn=ntt_sn,
                    title=f"새 공지 ({ntt_sn})",
                    url=normalize_notice_url(
                        f"/badaro/na/ntt/selectNttInfo.do?nttSn={ntt_sn}&mi=4370"
                    ),
                ),
            )

    notices = list(found.values())
    notices.sort(key=lambda item: int(item.ntt_sn), reverse=True)
    return notices


def is_notice_html(html: str) -> bool:
    return "nttSn=" in html and "selectNttInfo" in html


def fetch_page(session: requests.Session) -> str:
    session.get(WARMUP_URL, timeout=30)
    response = session.get(
        NOTICE_LIST_URL,
        timeout=30,
        headers={"Referer": WARMUP_URL},
    )
    response.encoding = "utf-8"
    html = response.text
    # 이 사이트는 정상 목록을 주면서도 404를 내리는 경우가 있습니다.
    if is_notice_html(html):
        return html
    response.raise_for_status()
    raise RuntimeError("공지 목록을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")


def fetch_notices() -> list[Notice]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            session = requests.Session()
            session.headers.update(REQUEST_HEADERS)
            notices = parse_notices(fetch_page(session))
            if not notices:
                raise RuntimeError("공지 목록을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")
            return notices
        except Exception as exc:  # noqa: BLE001 - 네트워크/파싱 오류를 모아 재시도
            last_error = exc
            logging.warning("공지 확인 실패 (%s/3): %s", attempt, exc)
            time.sleep(min(5 * attempt, 15))
    raise RuntimeError(f"공지 페이지를 가져오지 못했습니다: {last_error}")


def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        payload = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("본 공지 저장 파일을 읽지 못했습니다. 새로 시작합니다: %s", exc)
        return set()
    ids = payload.get("ids", payload if isinstance(payload, list) else [])
    return {str(item) for item in ids}


def save_seen(ids: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ids": sorted(ids, key=lambda value: int(value) if value.isdigit() else value, reverse=True),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp = SEEN_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SEEN_PATH)


PRIORITY_MAP = {
    "min": 1,
    "low": 2,
    "default": 3,
    "high": 4,
    "urgent": 5,
    "max": 5,
}


def ntfy_priority(value: str) -> int:
    text = (value or "high").strip().lower()
    if text.isdigit():
        return max(1, min(5, int(text)))
    return PRIORITY_MAP.get(text, 4)


def send_ntfy(env: dict[str, str], notice: Notice, *, test: bool = False) -> None:
    topic = ensure_topic(env)
    server = env_value(env, "NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    prefix = "[테스트] " if test else ""
    title = f"{prefix}{notice.title}"
    lines = ["승선생활관 새 공지"]
    if notice.date:
        lines.append(f"등록일: {notice.date}")
    if notice.author:
        lines.append(f"작성자: {notice.author}")
    lines.append(notice.url)

    # 한글 제목은 HTTP 헤더(latin-1)로 보내면 깨지므로 JSON 본문으로 보냅니다.
    payload = {
        "topic": topic,
        "title": title,
        "message": "\n".join(lines),
        "priority": ntfy_priority(env_value(env, "NTFY_PRIORITY", "high")),
        "tags": ["loudspeaker"],
        "click": notice.url,
        "actions": [
            {
                "action": "view",
                "label": "공지 열기",
                "url": notice.url,
            }
        ],
    }
    response = requests.post(server, json=payload, timeout=30)
    response.raise_for_status()
    logging.info("알림 전송: %s (%s)", notice.title, notice.ntt_sn)


def check_once(env: dict[str, str]) -> int:
    notices = fetch_notices()
    seen = load_seen()
    current_ids = {notice.ntt_sn for notice in notices}

    if not seen:
        save_seen(current_ids)
        logging.info("처음 실행입니다. 기존 공지 %s건을 기준으로 저장하고 알림은 보내지 않습니다.", len(current_ids))
        return 0

    new_notices = [notice for notice in notices if notice.ntt_sn not in seen]
    if not new_notices:
        logging.info("새 공지 없음. 현재 목록 %s건.", len(notices))
        save_seen(seen | current_ids)
        return 0

    new_notices.sort(key=lambda item: int(item.ntt_sn))
    sent = 0
    for notice in new_notices:
        try:
            send_ntfy(env, notice)
            seen.add(notice.ntt_sn)
            save_seen(seen | current_ids)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logging.error("알림 전송 실패 (%s): %s", notice.ntt_sn, exc)

    logging.info("새 공지 %s건 중 %s건 알림 완료.", len(new_notices), sent)
    return 0 if sent == len(new_notices) else 1


def run_test(env: dict[str, str]) -> int:
    notices = fetch_notices()
    latest = notices[0]
    logging.info("테스트 알림 대상: %s (%s)", latest.title, latest.ntt_sn)
    send_ntfy(env, latest, test=True)
    print(f"테스트 알림을 보냈습니다: {latest.title}")
    print(f"등록일: {latest.date or '없음'}")
    print(f"링크: {latest.url}")
    print(f"ntfy 토픽: {ensure_topic(env)}")
    return 0


def watch_loop(env: dict[str, str]) -> int:
    interval = int(env_value(env, "CHECK_INTERVAL_SECONDS", "300") or "300")
    logging.info("%s초마다 공지를 확인합니다.", interval)
    while True:
        try:
            check_once(env)
        except Exception as exc:  # noqa: BLE001
            logging.error("이번 확인은 실패했지만 계속 실행합니다: %s", exc)
        time.sleep(max(interval, 60))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="승선생활관 공지 ntfy 알림")
    parser.add_argument("--test", action="store_true", help="지금 최신 공지 1개를 알림으로 보냅니다")
    parser.add_argument("--watch", action="store_true", help="종료하지 않고 주기적으로 확인합니다")
    return parser.parse_args()


def main() -> int:
    os.chdir(ROOT)
    setup_logging()
    args = parse_args()
    env = load_env()

    try:
        if args.test:
            return run_test(env)
        if args.watch:
            return watch_loop(env)
        return check_once(env)
    except Exception as exc:  # noqa: BLE001
        logging.error("실행 실패: %s", exc)
        if args.test or sys.stdout.isatty():
            print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
