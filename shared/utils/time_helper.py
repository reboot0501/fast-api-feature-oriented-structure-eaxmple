# shared/utils/time_helper.py

from datetime import datetime, timedelta

def get_current_time() -> str:
    """현재 시간을 ISO Format 으로 반환"""
    return datetime.now().isoformat()

def get_days_to_now(days: int) -> str:
    """현재 시간에 특정 일수를 추가 하여 반환"""
    return (datetime.now() + timedelta(days=days)).isoformat()

""" 사용 예시
from shared.utils.logging_helper import logger
from shared.utils.time_helper import get_current_time, get_days_to_now

logger.info("현재 시간: %s", get_current_time()) ## 공통 함수 사용
"""
