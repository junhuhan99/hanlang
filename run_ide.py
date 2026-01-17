#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한랭 IDE 실행 스크립트
"""

import sys
import os

# 현재 디렉토리를 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from hanlang_ide import main

if __name__ == "__main__":
    main()
