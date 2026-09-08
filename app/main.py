# app/main.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# 프로젝트 루트 디렉터리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# .env 파일의 환경 변수 로드
load_dotenv()

# app.app에 정의 및 라우터 등록된 app 인스턴스 import
from app.app import app

HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", 8000))

@app.get("/")
def read_root():
  return {"message": "Welcome to FastAPI Feature-Oriented Example!!!"}

if __name__ == "__main__":
  uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)

