# shared/utils/logging.py

import os

import logging

# 로그 파일 경로 설정
LOG_FILE_PATH = "logs/app.log"
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True) # loss 폴더 생성

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO, # 로깅 레벨 성정
    format="%(asctime)s [%(levelname)s] %(message)s", # 로깅 포맷 설정
    handlers=[
        logging.StreamHandler(), # 터미털 출력
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8') # 파일 핸들러 설정
    ]
)

# 로거 가져 오기
logger = logging.getLogger("fapi") # looger 정의, 로거를 여러개 만든 다면, 로거 이음을 각각 사용해 구분 할 수 있다.
logger.info("로깅 설정 완료")

"""
from utils.logging import  logger

def items():
    logger.info("items")
    return [
        {
            "item_id": "1",
            "item_name": "자바"
        },
        {
            "item_id": "2",
            "item_name": "파이썬"
        },
    ]

"""


