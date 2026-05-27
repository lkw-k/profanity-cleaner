import os                           #  환경변수 읽기
import discord                      # 디스코드 라이브러리
from discord.ext import commands    # 디스코드 봇 명령어
from dotenv import load_dotenv      # .env 파일 읽기

load_dotenv() # .env 파일에서 환경변수 읽기
TOKEN = os.getenv('DISCORD_TOKEN') # 환경변수에서 DISCORD_TOKEN 읽기

intents = discord.Intents.default() # 디스코드 봇의 권한 설정
intents.message_content = True # 메시지 내용 읽기 권한 활성화

bot = commands.Bot(commands_prefix='!', intents=intents) # 봇 객체 생성

@bot.event
async def on_ready():
    print(f"봇 로그인 성공 : {bot.user.name}")  # 봇이 로그인되면 콘솔에 메시지 출력
