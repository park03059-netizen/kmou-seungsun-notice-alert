# 승선생활관 공지 알림

한국해양대학교 승선생활관 **생활교육지도관 공지사항**에 새 글이 올라오면, iPhone 상단에 제목과 함께 ntfy 알림 배너가 뜹니다.

- 대상 페이지: [생활교육지도관 공지사항](https://www.kmou.ac.kr/badaro/na/ntt/selectNttList.do?mi=4370&bbsId=10003004)
- 확인 주기: 5분
- **PC가 꺼져 있어도** GitHub Actions가 대신 확인합니다.
- 처음 실행할 때는 이미 올라와 있는 글을 알림으로 보내지 않습니다.
- 같은 글은 `nttSn` 고유번호로 기억해서 다시 보내지 않습니다.

## 클라우드 동작 (기본)

GitHub에 올라간 뒤부터는 아래처럼 동작합니다.

1. 5분마다 GitHub 서버가 공지 페이지를 확인합니다.
2. 새 글이 있으면 ntfy로 iPhone에 알림을 보냅니다.
3. 본인 PC를 켤 필요는 없습니다. Cursor를 켤 필요도 없습니다.

토픽 이름 `NTFY_TOPIC`은 GitHub Secrets에만 넣고, 저장소에는 넣지 않습니다.

로컬 PC 자동 시작과 클라우드를 같이 켜 두면 알림이 두 번 갈 수 있습니다. 클라우드를 쓰는 동안에는 `uninstall_autostart.bat`으로 PC 자동 확인을 끄세요.

## iPhone ntfy

1. App Store에서 **ntfy** 앱을 설치합니다.
2. 토픽 `kmou-seungsun-292760` 을 구독합니다. 나중에 바꾸면 `.env`와 GitHub Secret을 같이 바꿔야 합니다.
3. iPhone 설정 > 알림 > ntfy에서 알림 허용, 잠금 화면, 배너를 켭니다.

## 로컬에서 테스트할 때

PC에서 알림만 시험하려면 `test_notify.bat`을 실행합니다.

```bat
.venv\Scripts\python.exe watcher.py
.venv\Scripts\python.exe watcher.py --test
```

## 로컬 자동 시작 (선택)

PC가 켜져 있을 때만 확인하고 싶다면 `install_autostart.bat`을 한 번 실행합니다. 끌 때는 `uninstall_autostart.bat`을 실행합니다.

클라우드와 동시에 쓰지 마세요.

## 동작 방식

1. 공지 목록 페이지를 읽습니다.
2. 각 글의 `nttSn` 번호를 고유값으로 사용합니다. 제목이 같아도 다른 글로 취급합니다.
3. `data/seen.json`에 이미 본 글 번호를 저장합니다.
4. 처음 실행이면 현재 글을 기준으로만 저장하고 알림은 보내지 않습니다.
5. 그 다음부터 새로 생긴 `nttSn`만 ntfy로 보냅니다.

## 설정

로컬 테스트용 `.env`:

```
NTFY_TOPIC=kmou-seungsun-292760
NTFY_SERVER=https://ntfy.sh
NTFY_PRIORITY=high
CHECK_INTERVAL_SECONDS=300
```

클라우드에서는 GitHub Secret `NTFY_TOPIC`을 사용합니다.

## 알아둘 점

- GitHub Actions의 5분 주기는 가끔 몇 분 늦을 수 있습니다.
- 1페이지에 보이는 글만 확인합니다.
- 토픽 이름은 다른 사람이 추측하기 어렵게 두세요.

## 문제 해결

- **알림이 안 와요:** ntfy 토픽 이름, 알림 권한, 집중 모드를 확인하세요.
- **클라우드가 안 돌아요:** GitHub 저장소 Actions 탭에서 `Check dorm notices` 실행 기록을 보세요. Secrets에 `NTFY_TOPIC`이 있는지도 확인하세요.
- **처음부터 다시 하고 싶어요:** `data/seen.json`을 지우고 다시 실행하면 현재 글을 기준으로 다시 잡습니다.
