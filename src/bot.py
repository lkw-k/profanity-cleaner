import os                           # 환경변수 읽기
import discord                      # 디스코드 라이브러리
from discord.ext import commands    # 디스코드 봇 명령어
from dotenv import load_dotenv      # .env 파일 읽기
import json                         # JSON 파싱
import torch                        # PyTorch 버트 모델이라 파이토치 사용해야함
from transformers import AutoTokenizer, AutoModelForSequenceClassification  # kcbert 모델 불러오기
from groq import Groq
import database



load_dotenv()                                # .env 파일에서 환경변수 읽기
TOKEN = os.getenv('DISCORD_BOT_TOKEN')       # 환경변수에서 봇 토큰 읽기

# Groq API 키 설정
GROQ_API_KEY = os.getenv('GROQ_API_KEY')   # 환경변수에서 Groq API 키 읽기

#kcbert 모델 fhem (봇 시작할때 1회 실행)
MODEL_NAME = "illimax/kcbert-profanity"
print("모델 불러오는 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)   # 토크나이저 불러오기
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)  # 모델 불러오기
model.eval()  # 모델을 평가 모드로 설정 
print("모델 불러오기 완료")

groq_client = Groq(api_key=GROQ_API_KEY)
_groq_cache: dict[str, dict] = {}

# Groq에 보낼 프롬프트
SYSTEM_PROMPT = """한국어 비속어 정제 도구. 출력에 욕설·비속어를 절대 포함하지 마.

masked: 비속어를 같은 글자 수의 *로만 대체. 예) "아 시발 진짜" → "아 ** 진짜"
corrected: 문맥·감정을 유지하며 비속어를 순화된 표현으로 대체. 맞춤법도 정리. 예) "씨발 대박이다" → "와 대박이다"

JSON으로만 응답: {"masked": "...", "corrected": "..."}"""

FEEDBACK_EMOJI = "🏴"   # 욕설인데 감지 못한 경우
FALSE_POS_EMOJI = "🏳️"  # 욕설 아닌데 오탐된 경우 (봇 교정 답글에 달기)

intents = discord.Intents.default()          # 디스코드 봇의 권한 설정
intents.message_content = True               # 메시지 내용 읽기 권한 활성화
intents.reactions = True                     # 이모지 반응 감지 권한 활성화

bot = commands.Bot(command_prefix='!', intents=intents)   # 봇 객체 생성

def is_profanity(text: str) -> bool:
    """kcbert로 비속어 여부 판정. 비속어면 True"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)  # 텍스트 토큰화
    with torch.no_grad():  # 그래디언트 계산 비활성화
        outputs = model(**inputs)  # 모델에 입력 전달
    pred = torch.argmax(outputs.logits, dim=1).item()
    return pred == 1  # 1이면 비속어, 0이면 정상

def clean_with_groq(text: str) -> dict:
    """Groq에 마스킹+교정 요청. {'masked': ..., 'corrected': ...} 반환."""
    if text in _groq_cache:
        return _groq_cache[text]
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=200,
    )
    result_text = response.choices[0].message.content
    result = json.loads(result_text)
    _groq_cache[text] = result
    return result

@bot.event
async def on_ready():
    database.init_db()
    print(f"봇 로그인 성공 : {bot.user.name}")   # 봇이 로그인되면 콘솔에 메시지 출력

@bot.event
async def on_message(message):
    if message.author == bot.user:              # 봇 자신의 메시지는 무시
        return
    if not message.content.startswith('!'):
        print(f"감지: {message.content}")
        # KcBERT 비속어 판정
        if is_profanity(message.content):
            try:
                # Groq에 마스킹+교정 요청
                result = clean_with_groq(message.content)
                reply = (
                    f"원문: {result['masked']}\n"
                    f"교정: {result['corrected']}"
                )
                # 원본 메시지에 답글로 응답
                await message.reply(reply)
            except Exception as e:
                print(f"Groq 호출 실패: {e}")
                await message.channel.send("교정 중 오류가 발생했어요")
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    emoji = str(payload.emoji)
    if emoji not in (FEEDBACK_EMOJI, FALSE_POS_EMOJI):
        return
    try:
        channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if emoji == FEEDBACK_EMOJI:
            # 🚩: 욕설인데 봇이 감지 못한 메시지 → label=1 저장
            if message.author == bot.user:
                return
            if database.is_already_saved(str(payload.message_id)):
                return
            result = clean_with_groq(message.content)
            await message.reply(f"원문: {result['masked']}\n교정: {result['corrected']}")
            database.save_profanity(str(payload.message_id), message.content)

        elif emoji == FALSE_POS_EMOJI:
            # ✅: 봇의 교정 답글에 달면 오탐 피드백 → 원본 메시지 label=0 저장
            if message.author != bot.user:
                return
            if not message.reference:
                return
            original = await channel.fetch_message(message.reference.message_id)
            if database.is_already_saved(str(original.id)):
                return
            database.save_false_positive(str(original.id), original.content)
            await message.add_reaction("👍")

    except Exception as e:
        print(f"반응 처리 오류: {e}")


@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('pong')                   # !ping 명령어에 'pong' 응답


# 봇 실행
if TOKEN:
    bot.run(TOKEN)                           # 토큰이 있으면 봇 실행
else:
    print("토큰이 없습니다! .env 파일을 확인하세요")   # 토큰 없으면 에러 출력