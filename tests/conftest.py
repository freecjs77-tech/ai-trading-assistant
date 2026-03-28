"""
tests/conftest.py — pytest 공통 설정
"""
import sys
from pathlib import Path

# src 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
