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

봇이 욕설을 감지하지 못한 경우, 해당 메시지에 🚩 이모지를 달면 수동으로 처리할 수 있습니다.

```
봇이 욕설 감지 실패 (무반응)
        ↓
사용자가 해당 메시지에 🚩 반응
        ↓
봇이 Groq로 마스킹/교정 처리 후 reply
        ↓
해당 메시지를 욕설 데이터로 feedback.db에 저장
```

- 같은 메시지에 🚩을 여러 번 달아도 중복 처리되지 않습니다.
- 봇 자신이 보낸 메시지에는 반응하지 않습니다.
- 저장된 데이터는 나중에 `!train` 명령어로 모델 학습에 활용될 예정입니다.

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

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들고 아래 값을 입력합니다.

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
GROQ_API_KEY=your_groq_api_key
```

### 3. 봇 실행

```bash
python src/bot.py
```

## Discord 봇 권한

봇에 다음 권한이 필요합니다.

- `Message Content Intent` 활성화 (Discord Developer Portal > Bot 설정)
- 채널 메시지 읽기 / 쓰기 권한

## 명령어

| 명령어 | 설명 |
|---|---|
| `!ping` | 봇 응답 확인 (`pong` 반환) |
