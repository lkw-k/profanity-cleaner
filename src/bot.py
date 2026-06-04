import os                           # 환경변수 읽기
import discord                      # 디스코드 라이브러리
from discord.ext import commands    # 디스코드 봇 명령어
from dotenv import load_dotenv      # .env 파일 읽기
import json                         # JSON 파싱
import torch                        # PyTorch 버트 모델이라 파이토치 사용해야함
from transformers import AutoTokenizer, AutoModelForSequenceClassification  # kcbert 모델 불러오기
from groq import Groq



load_dotenv()                                # .env 파일에서 환경변수 읽기
TOKEN = os.getenv('DISCORD_BOT_TOKEN')       # 환경변수에서 봇 토큰 읽기

# Groq API 키 설정
groq_api_key = os.getenv('GROQ_API_KEY')   # 환경변수에서 Groq API 키 읽기

#kcbert 모델 fhem (봇 시작할때 1회 실행)
MODEL_NAME = "illimax/kcbert-profanity"
print("모델 불러오는 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)   # 토크나이저 불러오기
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)  # 모델 불러오기
model.eval()  # 모델을 평가 모드로 설정 
print("모델 불러오기 완료")

groq_client = Groq(api_key=GROQ_API_KEY)

# Groq에 보낼 프롬프트
SYSTEM_PROMPT = """너는 한국어 비속어를 처리하는 도구야. 입력 문장을 받아 다음 두 가지를 만들어:

1. masked: 비속어 부분만 같은 글자 수의 *로 가린 버전
   - 예: "시발" (2글자) → "**"
   - 예: "병신새끼" (4글자) → "****"
   - 비속어가 아닌 부분은 그대로 둠

2. corrected: 비속어를 자연스러운 표현으로 바꾸고 맞춤법도 고친 버전
   - 욕설/혐오 표현은 자연스러운 한국어로 대체
   - 띄어쓰기, 맞춤법 정리

반드시 아래 JSON 형식으로만 응답해. 설명, 마크다운, 다른 텍스트 절대 추가 금지.

{"masked": "...", "corrected": "..."}"""

intents = discord.Intents.default()          # 디스코드 봇의 권한 설정
intents.message_content = True               # 메시지 내용 읽기 권한 활성화

bot = commands.Bot(command_prefix='!', intents=intents)   # 봇 객체 생성

def is_profanity(text: str) -> bool:
    """kcbert로 비속어 여부 판정. 비속어면 True"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)  # 텍스트 토큰화
    with torch.no_grad():  # 그래디언트 계산 비활성화
        outputs = model(**inputs)  # 모델에 입력 전달
    pred = torch.argmax(outputs.logits, dim=1).item()
    return pred == 1  # 1이면 비속어, 0이면 정상

@bot.event
async def on_ready():
    print(f"봇 로그인 성공 : {bot.user.name}")   # 봇이 로그인되면 콘솔에 메시지 출력

@bot.event
async def on_message(message):
    if message.author == bot.user:              # 봇 자신의 메시지는 무시
        return
    print(f"감지: {message.content}") 
    await bot.process_commands(message)

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('pong')                   # !ping 명령어에 'pong' 응답


# 봇 실행
if TOKEN:
    bot.run(TOKEN)                           # 토큰이 있으면 봇 실행
else:
    print("토큰이 없습니다! .env 파일을 확인하세요")   # 토큰 없으면 에러 출력