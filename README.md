# profanity-cleaner

한국어 비속어를 자동으로 감지하고 마스킹/교정해주는 Discord 봇입니다.

## 동작 방식

메시지가 올라오면 두 단계로 처리합니다.

1. **KcBERT로 비속어 판정** — `illimax/kcbert-profanity` 모델이 메시지가 비속어인지 아닌지를 분류합니다.
2. **Groq(LLaMA 3.3 70B)으로 마스킹 + 교정** — 비속어로 판정된 메시지를 Groq API에 보내 두 가지 결과를 받습니다.
   - `원문`: 비속어 부분을 같은 글자 수의 `*`로 가린 버전
   - `교정`: 비속어를 자연스러운 표현으로 바꾸고 맞춤법까지 고친 버전

비속어가 감지되면 원본 메시지에 답글(reply)로 결과를 전달합니다.

## 이모지 피드백 파이프라인

깃발 이모지 두 개로 봇의 판정을 교정합니다. 색에 따라 다는 위치와 동작이 다릅니다.

| 이모지 | 어디에 다나 | 무슨 뜻 | 봇 동작 |
|---|---|---|---|
| 🏴 검은 깃발 | 사용자의 **원본 메시지** | 욕설인데 봇이 못 잡았다 (미탐) | Groq로 마스킹/교정 후 답글 + `label=1`로 저장 |
| 🏳️ 흰 깃발 | 봇의 **교정 답글** | 욕설이 아닌데 잡혔다 (오탐) | 답글이 가리키는 원본을 `label=0`으로 저장 |

```
[미탐] 봇이 욕설 감지 실패 (무반응)
        ↓  사용자가 원본 메시지에 🏴
   마스킹/교정 답글 + feedback.db에 욕설(label=1) 저장

[오탐] 봇이 멀쩡한 말을 욕설로 교정
        ↓  사용자가 봇 답글에 🏳️
   원본을 feedback.db에 정상(label=0) 저장 + 👍 반응
```

- 🏳️ 처리에 성공하면 👍, 두 깃발 모두 규칙에 맞지 않으면 ❌ 반응이 달립니다. ❌가 붙는 경우는 다음과 같습니다.
  - 🏴을 봇 메시지나 마스킹 재게시본에 단 경우 (재게시본은 내용이 `***`라 학습에 못 씁니다)
  - 🏳️를 봇 답글이 아닌 메시지에 단 경우
  - 봇 재시작으로 삭제된 원본 내용을 잃은 경우
  - 이미 저장된 메시지인 경우 (중복 저장 방지)
- 봇 자신의 반응은 무시합니다.
- Discord가 이형 선택자(U+FE0F)를 붙이든 말든 같은 깃발로 인식합니다.
- 저장된 데이터는 `!train` 명령어로 모델 학습에 사용합니다.

## 개선 전후 비교

모델 교체와 프롬프트 개선으로 비속어 누출률을 7.1% → 0.6%로 낮춘 측정 기록은 [docs/benchmark.md](docs/benchmark.md)에 있습니다.

## 기술 스택

| 역할 | 도구 |
|---|---|
| Discord 봇 | `discord.py` |
| 비속어 분류 | KcBERT (`illimax/kcbert-profanity`) + PyTorch |
| 마스킹/교정 | Groq API (llama-3.3-70b-versatile) |
| 환경변수 관리 | `python-dotenv` |

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install discord.py python-dotenv torch transformers groq
```

### 2. 봇 실행

```bash
python src/bot.py
```

## Discord 봇 권한

봇에 다음 권한이 필요합니다.

- `Message Content Intent` 활성화 (Discord Developer Portal > Bot 설정)
- 채널 메시지 읽기 / 쓰기 권한
- `Manage Messages` — 욕설 원본 메시지 삭제
- `Manage Webhooks` — 작성자 명의로 마스킹본 재게시

`Manage Messages` / `Manage Webhooks`가 없으면 원본을 지우지 못하고, 기존처럼 답글로만 마스킹·교정 결과를 알립니다.

스레드 안에서는 웹훅 재게시가 동작하지 않고 답글로 폴백합니다. DM도 마찬가지입니다.

## 명령어

| 명령어 | 설명 |
|---|---|
| `!ping` | 봇 응답 확인 (`pong` 반환) |

## 리눅스 서버 배포 (systemd)

Discord 봇은 서버에서 Discord로 나가는 연결만 사용합니다. 열어야 할 포트나 도메인, 리버스 프록시가 필요 없고 프로세스를 계속 띄워두기만 하면 됩니다.

### 1. 서버에 코드 받기

```bash
ssh 계정@학교서버주소
git clone https://github.com/사용자명/profanity-cleaner.git
cd profanity-cleaner
```

### 2. 가상환경 + 의존성 (CPU 전용)

`pyproject.toml`은 CUDA용 torch를 지정하므로, GPU가 없는 서버에서는 `uv sync` 대신 CPU 빌드를 직접 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv 없을 때만
uv venv --python 3.11
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install "discord.py" python-dotenv "transformers<4.50" groq
```

### 3. 환경변수

```bash
cp .env.example .env
nano .env     # 토큰 입력
chmod 600 .env
```

### 4. 동작 확인

```bash
.venv/bin/python src/bot.py
```

`봇 로그인 성공 : ...`이 뜨면 Ctrl+C로 종료합니다. 최초 실행 시 KcBERT 모델(약 500MB)을 `~/.cache/huggingface`에 내려받습니다.

### 5. systemd 등록

```bash
sed "s/__USER__/$USER/g" deploy/profanity-cleaner.service | sudo tee /etc/systemd/system/profanity-cleaner.service
sudo systemctl daemon-reload
sudo systemctl enable --now profanity-cleaner
```

`WorkingDirectory`가 `/home/$USER/profanity-cleaner` 기준이므로, 다른 경로에 클론했다면 유닛 파일의 경로를 수정해야 합니다.

### 6. 운영

```bash
sudo systemctl status profanity-cleaner    # 상태 확인
sudo journalctl -u profanity-cleaner -f    # 로그 실시간 확인
sudo systemctl restart profanity-cleaner   # 재시작

git pull && sudo systemctl restart profanity-cleaner   # 코드 업데이트
```
