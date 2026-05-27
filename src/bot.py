import os                           # 환경변수 읽기
import discord                      # 디스코드 라이브러리
from discord.ext import commands    # 디스코드 봇 명령어
from dotenv import load_dotenv      # .env 파일 읽기

load_dotenv()                                # .env 파일에서 환경변수 읽기
TOKEN = os.getenv('DISCORD_BOT_TOKEN')       # 환경변수에서 봇 토큰 읽기

intents = discord.Intents.default()          # 디스코드 봇의 권한 설정
intents.message_content = True               # 메시지 내용 읽기 권한 활성화

bot = commands.Bot(command_prefix='!', intents=intents)   # 봇 객체 생성


@bot.event
async def on_ready():
    print(f"봇 로그인 성공 : {bot.user.name}")   # 봇이 로그인되면 콘솔에 메시지 출력


@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('pong')                   # !ping 명령어에 'pong' 응답


# 봇 실행
if TOKEN:
    bot.run(TOKEN)                           # 토큰이 있으면 봇 실행
else:
    print("토큰이 없습니다! .env 파일을 확인하세요")   # 토큰 없으면 에러 출력