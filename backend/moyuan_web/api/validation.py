"""
API 校验常量 —— 请求模型和路由参数共用的正则模式

【基础知识】
- 正则校验模式：用于 Pydantic 模型的 Field(pattern=...) 参数，
  在请求进入业务逻辑前就拦截不合法的输入，防止注入攻击或数据污染。

- 各模式说明：
  - NON_BLANK_TEXT_PATTERN：至少包含一个非空白字符，防止用户提交纯空格
  - SESSION_ID_PATTERN：会话ID格式，字母数字开头，支持 .:_- 分隔符
  - MODEL_ID_PATTERN：模型ID格式，与会话ID规则一致
  - SHARE_ID_PATTERN：分享ID格式，10位十六进制字符串（如 a1b2c3d4e5）
  - CITY_ID_PATTERN：城市ID格式，小写字母数字加连字符（如 bei-jing）
"""

from __future__ import annotations


NON_BLANK_TEXT_PATTERN = r".*\S.*"  # 至少一个非空白字符，例："hello" ✓, "   " ✗
SESSION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"  # 会话ID：字母数字开头，最长128字符
MODEL_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"  # 模型ID：与会话ID格式一致
SHARE_ID_PATTERN = r"^[a-f0-9]{10}$"  # 分享ID：10位十六进制，例："a1b2c3d4e5"
CITY_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"  # 城市ID：小写字母数字+连字符，例："shang-hai"
