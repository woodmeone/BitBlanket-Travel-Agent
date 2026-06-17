"""项目路径引导模块 —— 确保所有模块都能正确找到彼此。

基础知识：
  - sys.path: Python 的模块搜索路径列表，import 语句会按此列表顺序查找模块
  - 当项目结构较深时，子包可能无法 import 兄弟包，需要手动将路径加入 sys.path

本模块将项目根目录和 backend 目录加入 sys.path，使得：
  - agent.travel_agent... 等 Agent 包可被正确导入
  - moyuan_web... 等 Web 包可被正确导入
"""

from __future__ import annotations

import sys
from pathlib import Path  # pathlib: Python 3.4+ 的路径操作库，比 os.path 更面向对象

# Path(__file__).resolve().parents[2] 表示当前文件向上 2 层目录
# 即从 backend/moyuan_web/bootstrap.py → moyuan-travel-agent/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"  # backend 子目录


def ensure_project_paths() -> None:
    """确保项目根目录和 backend 包路径可被 import。

    将路径插入 sys.path 开头（insert(0, ...)），使其优先于系统包。
    如果路径已存在则跳过，避免重复添加。

    应用场景举例：
      当 ChatService 中执行 from agent.travel_agent... 时，
      Python 需要在 sys.path 中找到 agent 包，此函数确保这一点。
    """
    for path in (str(PROJECT_ROOT), str(BACKEND_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
