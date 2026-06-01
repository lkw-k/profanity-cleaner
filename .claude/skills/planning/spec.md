# Profanity Cleaner Discord Bot — 구현 스펙

## 개요
Discord에서 한국어/영어 비속어를 자동 감지하고, 경고 메시지를 전송하며 비속어를 `***`로 마스킹하는 봇.

---

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| 지원 언어 | 한국어 + 영어 |
| 언어 감지 방식 | 두 모델 동시 실행 후 OR 조합 |
| 한국어 모델 | KCBERT (beomi/kcbert-base) 파인튜닝 → HF Hub 업로드 |
| 영어 모델 | unitary/toxic-bert (기존 파인튜닝 모델 그대로 사용) |
| 신뢰도 임계값 | 0.7 이상이면 비속어로 판단 |
| 감지 시 액션 | 원본 메시지 삭제 + 경고 메시지 전송 + 마스킹된 메시지 재전송 |
| 마스킹 방식 | 사전(wordlist) 기반 — 등록된 단어를 `***`로 치환 |
| 경고 정책 | 매번 경고 (횟수 제한 없음) |
| 플랫폼 | Discord (discord.py) |
| 모델 저장 | Hugging Face Hub 업로드 후 `from_pretrained('username/model')` |
| 배포 | 일단 로컬 Windows PC, 추후 클라우드 |

---

## 시스템 아키텍처

```
Discord 메시지 수신
        ↓
[on_message 핸들러]
        ↓
  두 모델 동시 실행
  ┌─────────────────┐
  │ KCBERT (한국어)  │  + toxic-bert (영어)
  └─────────────────┘
        ↓
  OR 조합 — 하나라도 confidence > 0.7 이면 비속어
        ↓ (비속어 감지됨)
  1. 원본 메시지 삭제
  2. wordlist로 비속어 단어 *** 마스킹
  3. 마스킹된 메시지 재전송
  4. 경고 메시지 전송
```

---

## 구현 단계

### Phase 1 — KCBERT 파인튜닝 완성 (notebooks/01_data_explore.ipynb 이어서)
- [ ] `TrainingArguments` 설정 (epochs=3, batch_size=16, lr=2e-5)
- [ ] `Trainer` 설정 및 `trainer.train()` 실행
- [ ] 검증셋 평가 (`trainer.evaluate()`)
- [ ] `model.save_pretrained()` + `push_to_hub('username/kcbert-profanity')`

### Phase 2 — 추론 모듈 (src/detector.py)
- [ ] `ProfanityDetector` 클래스
  - `__init__`: KCBERT + toxic-bert 두 모델 로드
  - `detect(text) -> bool`: OR 조합, threshold=0.7
  - `mask(text) -> str`: wordlist 기반 마스킹
- [ ] 한국어/영어 비속어 wordlist 파일 (`data/wordlist_ko.txt`, `data/wordlist_en.txt`)

### Phase 3 — Discord 봇 (bot.py)
- [ ] `discord.Intents` 설정 (message_content 활성화)
- [ ] `on_message` 이벤트 핸들러
  - 봇 메시지 무시
  - `detector.detect(message.content)` 호출
  - 비속어 감지 시:
    1. `message.delete()`
    2. `detector.mask(message.content)` 로 마스킹
    3. 채널에 마스킹된 메시지 재전송 (`[username]: ***마스킹된 내용***`)
    4. 경고 임베드 메시지 전송
- [ ] `.env`에 `DISCORD_TOKEN` 관리

### Phase 4 — 통합 테스트
- [ ] 한국어 비속어 메시지 테스트
- [ ] 영어 비속어 메시지 테스트
- [ ] 정상 메시지 오탐 여부 확인
- [ ] 한영 혼합 메시지 테스트

---

## 프로젝트 구조 (목표)

```
profanity-cleaner/
├── notebooks/
│   └── 01_data_explore.ipynb   # KCBERT 학습 (현재 여기까지 됨)
├── src/
│   └── detector.py             # ProfanityDetector 클래스
├── data/
│   ├── wordlist_ko.txt         # 한국어 비속어 사전
│   └── wordlist_en.txt         # 영어 비속어 사전
├── bot.py                      # Discord 봇 진입점
├── .env                        # DISCORD_TOKEN
└── requirements.txt
```

---

## 핵심 의존성

```
discord.py
transformers
torch
datasets
python-dotenv
scikit-learn
```

---

## 다음 첫 번째 액션
노트북에서 `TrainingArguments` + `Trainer` 설정 추가 후 학습 실행.
