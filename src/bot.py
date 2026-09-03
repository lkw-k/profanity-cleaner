import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import torch
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from safetensors.torch import load as load_safetensors
from groq import Groq
import database



load_dotenv()                                # .env 파일에서 환경변수 읽기
TOKEN = os.getenv('DISCORD_BOT_TOKEN')       # 환경변수에서 봇 토큰 읽기

# Groq API 키 설정
GROQ_API_KEY = os.getenv('GROQ_API_KEY')   # 환경변수에서 Groq API 키 읽기

#kcbert 모델 fhem (봇 시작할때 1회 실행)
MODEL_NAME = "illimax/kcbert-profanity"
TRAINED_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'trained')
WEIGHTS_FILE = os.path.join(TRAINED_PATH, 'model.safetensors')
print("모델 불러오는 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)   # 토크나이저 불러오기 (학습해도 안 바뀜)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)  # 모델 불러오기
if os.path.isfile(WEIGHTS_FILE):
    # from_pretrained(TRAINED_PATH)로 읽으면 safetensors가 이 파일을 mmap으로 붙잡아
    # 다음 !train의 저장이 윈도우에서 os error 1224로 실패한다.
    # bytes로 읽어 넣으면 파일 핸들이 남지 않는다.
    with open(WEIGHTS_FILE, 'rb') as fh:
        model.load_state_dict(load_safetensors(fh.read()))
    print(f"학습된 가중치 적용: {WEIGHTS_FILE}")
# 학습된 가중치까지 올린 뒤 한 번에 옮긴다. 파라미터마다 host->device 복사가 따로 일어나지 않는다.
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(DEVICE)
model.eval()  # 모델을 평가 모드로 설정
print(f"모델 불러오기 완료 (device={DEVICE})")

groq_client = Groq(api_key=GROQ_API_KEY)
_groq_cache: dict[str, dict] = {}

# Groq에 보낼 프롬프트
SYSTEM_PROMPT = """한국어 비속어 마스킹/교정 도구.

masked: 비속어 글자만 같은 개수의 *로 바꾼다. 조사·어미는 남긴다. 비속어를 하나도 빠뜨리지 마라.
corrected: 비속어를 순화하고 맞춤법을 정리한다. 문맥은 유지.

예) "야 이 개새끼야 시발 존나 짜증나"
{"masked": "야 이 ***야 ** ** 짜증나", "corrected": "야 너 정말 짜증나"}

JSON으로만 응답: {"masked": "...", "corrected": "..."}"""

FEEDBACK_EMOJI = "🏴"   # 욕설인데 감지 못한 경우
FALSE_POS_EMOJI = "🏳️"  # 욕설 아닌데 오탐된 경우 (봇 교정 답글에 달기)
# 같은 이모지라도 Discord가 이형 선택자(U+FE0F)를 붙여 보내기도, 빼고 보내기도 한다.
# 문자열을 그대로 비교하면 반응이 조용히 무시되므로 떼고 비교한다.
_FEEDBACK_KEY = FEEDBACK_EMOJI.replace('️', '')
_FALSE_POS_KEY = FALSE_POS_EMOJI.replace('️', '')

WEBHOOK_NAME = "profanity-cleaner"
_webhook_cache: dict[int, discord.Webhook] = {}
# 웹훅 재게시 메시지 id -> (원본 메시지 id, 원본 내용). 원본은 삭제되므로 오탐 피드백용으로 보관.
_masked_origin: dict[int, tuple[int, str]] = {}

_is_training = False

def _make_bar(current, total, width=20):
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100 * current // total
    return f"학습 중... [{bar}] {pct}% ({current}/{total} 에폭)"

def _run_epoch(texts, labels, optimizer):
    model.train()
    inputs = tokenizer(texts, return_tensors='pt', truncation=True, padding=True, max_length=128).to(DEVICE)
    label_tensor = torch.tensor(labels, device=DEVICE)
    optimizer.zero_grad()
    outputs = model(**inputs, labels=label_tensor)
    outputs.loss.backward()
    optimizer.step()
    model.eval()

def _save_model():
    # 토크나이저는 학습으로 바뀌지 않으므로 가중치만 저장한다.
    model.save_pretrained(TRAINED_PATH)

intents = discord.Intents.default()          # 디스코드 봇의 권한 설정
intents.message_content = True               # 메시지 내용 읽기 권한 활성화
intents.reactions = True                     # 이모지 반응 감지 권한 활성화

bot = commands.Bot(command_prefix='!', intents=intents)   # 봇 객체 생성

def is_profanity(text: str) -> bool:
    """kcbert로 비속어 여부 판정. 비속어면 True"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(DEVICE)  # 텍스트 토큰화
    with torch.no_grad():  # 그래디언트 계산 비활성화
        outputs = model(**inputs)  # 모델에 입력 전달
    pred = torch.argmax(outputs.logits, dim=1).item()
    return pred == 1  # 1이면 비속어, 0이면 정상

def clean_with_groq(text: str) -> dict:
    """Groq에 마스킹+교정 요청. {'masked': ..., 'corrected': ...} 반환."""
    if text in _groq_cache:
        return _groq_cache[text]
    response = groq_client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        # 추론을 끄지 않으면 추론 토큰이 max_tokens를 다 먹어 JSON이 잘린다.
        # 끄면 출력이 26~68토큰으로 떨어진다.
        reasoning_effort="none",
        max_tokens=200,
    )
    result_text = response.choices[0].message.content
    result = json.loads(result_text)
    _groq_cache[text] = result
    return result

async def _get_webhook(channel):
    """채널 웹훅을 확보한다. 매번 만들면 채널 웹훅 상한(10개)에 걸리므로 캐싱."""
    if channel.id in _webhook_cache:
        return _webhook_cache[channel.id]
    for wh in await channel.webhooks():
        if wh.name == WEBHOOK_NAME:
            _webhook_cache[channel.id] = wh
            return wh
    wh = await channel.create_webhook(name=WEBHOOK_NAME)
    _webhook_cache[channel.id] = wh
    return wh


async def mask_and_repost(message, result):
    """원본을 마스킹본으로 갈아끼우고 교정문을 답글로 단다.

    작성자 메시지는 봇이 수정할 수 없어 웹훅 재게시 + 삭제로 흉내낸다.
    재게시가 성공한 뒤에 삭제한다. 순서를 뒤집으면 실패 시 글이 영구 소실된다.
    """
    webhook = await _get_webhook(message.channel)
    posted = await webhook.send(
        result["masked"],
        username=message.author.display_name,
        avatar_url=message.author.display_avatar.url,
        wait=True,
    )
    _masked_origin[posted.id] = (message.id, message.content)
    try:
        await message.delete()
    except discord.NotFound:
        # 사용자가 먼저 지운 경우. 원본이 사라진 건 어차피 목적이므로 계속 진행한다.
        pass
    await message.channel.send(result["corrected"], reference=posted)


async def handle_profanity(message, result):
    """마스킹 재게시를 시도하고, 권한이 없으면 기존 답글 방식으로 폴백한다."""
    try:
        await mask_and_repost(message, result)
    except discord.Forbidden:
        # Manage Messages / Manage Webhooks 권한이 없는 채널
        print(f"권한 부족으로 답글 폴백: #{message.channel}")
        await message.reply(
            f"원문: {result['masked']}\n"
            f"교정: {result['corrected']}"
        )

@bot.event
async def on_ready():
    database.init_db()
    print(f"봇 로그인 성공 : {bot.user.name}")   # 봇이 로그인되면 콘솔에 메시지 출력

@bot.event
async def on_message(message):
    if message.author == bot.user:              # 봇 자신의 메시지는 무시
        return
    # 마스킹 재게시본은 author가 봇이 아니라 웹훅이라 위 조건에 안 걸린다. 재감지 방지.
    if message.webhook_id and message.webhook_id in {w.id for w in _webhook_cache.values()}:
        return
    if not message.content.startswith('!') and not _is_training:
        print(f"감지: {message.content}")
        # KcBERT 비속어 판정
        if is_profanity(message.content):
            try:
                # Groq에 마스킹+교정 요청
                result = clean_with_groq(message.content)
            except Exception as e:
                print(f"Groq 호출 실패: {e}")
                await message.channel.send("교정 중 오류가 발생했어요")
            else:
                await handle_profanity(message, result)
    await bot.process_commands(message)


async def _reject(message, reason):
    """피드백을 받았지만 처리하지 않았음을 알린다.

    조용히 return하면 사용자는 반응이 씹혔는지 규칙을 틀렸는지 알 수 없다.
    """
    print(f"피드백 무시: {reason} (msg={message.id})")
    try:
        await message.add_reaction("❌")
    except discord.HTTPException:
        pass


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    emoji = str(payload.emoji).replace('️', '')
    if emoji not in (_FEEDBACK_KEY, _FALSE_POS_KEY):
        return
    print(f"피드백 반응 수신: {[hex(ord(c)) for c in str(payload.emoji)]} msg={payload.message_id}")
    try:
        channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if emoji == _FEEDBACK_KEY:
            # 🏴: 욕설인데 봇이 감지 못한 메시지 → label=1 저장
            if message.author == bot.user:
                await _reject(message, "🏴는 원본 메시지에 답니다. 오탐 신고라면 이 답글에 🏳️")
                return
            if message.webhook_id:
                # 마스킹 재게시본. 내용이 이미 "***"라 학습 데이터로 쓸 수 없다.
                await _reject(message, "마스킹 재게시본에는 🏴를 달 수 없습니다")
                return
            if database.is_already_saved(str(payload.message_id)):
                await _reject(message, "이미 저장된 메시지")
                return
            result = clean_with_groq(message.content)
            # 재게시 과정에서 원본이 삭제되므로 저장을 먼저 한다.
            database.save_profanity(str(payload.message_id), message.content)
            await handle_profanity(message, result)

        elif emoji == _FALSE_POS_KEY:
            # 🏳️: 봇의 교정 답글에 달면 오탐 피드백 → 원본 메시지 label=0 저장
            if message.author != bot.user:
                await _reject(message, "🏳️는 봇의 교정 답글에 답니다")
                return
            if not message.reference:
                await _reject(message, "답글이 아니라 원본을 찾을 수 없습니다")
                return
            # 원본은 마스킹 재게시 과정에서 삭제됐으므로 보관해둔 값을 쓴다.
            origin = _masked_origin.get(message.reference.message_id)
            if origin is not None:
                original_id, original_content = origin
            else:
                # 폴백(답글만) 경로에서는 원본이 살아있다.
                original = await channel.fetch_message(message.reference.message_id)
                if original.webhook_id:
                    # 재시작으로 _masked_origin이 비었다. 재게시본은 "***"라 학습에 못 쓴다.
                    await _reject(message, "봇 재시작으로 원본 내용을 잃었습니다")
                    return
                original_id, original_content = original.id, original.content
            if database.is_already_saved(str(original_id)):
                await _reject(message, "이미 저장된 메시지")
                return
            database.save_false_positive(str(original_id), original_content)
            await message.add_reaction("👍")

    except Exception as e:
        print(f"반응 처리 오류: {e}")


@bot.command(name='train')
async def train_cmd(ctx):
    global _is_training
    if _is_training:
        await ctx.send("이미 학습 중입니다.")
        return

    # 이미 학습한 데이터를 다시 학습시키면 loss가 0인데도 로짓만 커져 오탐이 늘어난다.
    rows = database.get_untrained_feedback()
    if not rows:
        await ctx.send("새로 학습할 데이터가 없습니다. 🏴 또는 🏳️ 피드백을 먼저 달아주세요.")
        return

    message_ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]
    labels = [r[2] for r in rows]
    EPOCHS = 3
    optimizer = AdamW(model.parameters(), lr=2e-5)

    _is_training = True
    msg = await ctx.send(_make_bar(0, EPOCHS))
    loop = asyncio.get_event_loop()
    try:
        for epoch in range(EPOCHS):
            await loop.run_in_executor(None, lambda: _run_epoch(texts, labels, optimizer))
            await msg.edit(content=_make_bar(epoch + 1, EPOCHS))
        # 저장하지 않으면 봇 재시작 시 학습 결과가 사라진다.
        await msg.edit(content="학습 완료. 모델 저장 중...")
        await loop.run_in_executor(None, _save_model)
        # 저장이 끝난 뒤에 표시한다. 먼저 표시하면 저장 실패 시 데이터를 영영 못 쓴다.
        database.mark_trained(message_ids)
        await msg.edit(content=f"✅ 학습 완료! 새 데이터 {len(rows)}개 · {EPOCHS} 에폭 · 모델 저장됨")
    except Exception as e:
        await msg.edit(content=f"❌ 학습 실패: {e}")
        print(f"학습 오류: {e}")
    finally:
        _is_training = False


@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('pong')                   # !ping 명령어에 'pong' 응답


# 봇 실행
if TOKEN:
    bot.run(TOKEN)                           # 토큰이 있으면 봇 실행
else:
    print("토큰이 없습니다! .env 파일을 확인하세요")   # 토큰 없으면 에러 출력