"""记忆冲突解决 —— 处理新旧记忆的合并策略。

本模块负责检测和解决用户偏好冲突，当用户的新偏好与已存储的旧偏好矛盾时，
自动生成澄清提示，引导用户确认最终选择。

核心概念：
  - 偏好冲突（Preference Conflict）：用户前后表述的偏好不一致
    例如：之前说预算5000元，这次说预算10000元
  - 澄清提示（Clarification Hint）：Agent向用户发出的确认请求
    例如："你之前预算偏好是5000元，这次是10000元。本次按哪个预算执行？"
  - 冲突日志（Conflict Log）：记录所有冲突事件的审计日志
  - 待澄清队列（Pending Clarifications）：等待用户确认的冲突列表

典型场景（以"成都3日游"为例）：
  1. 用户第一次说"预算5000元"，Agent记住 budget_hint=5000
  2. 用户后来又说"这次预算1万元"，检测到预算冲突（2倍差异 + 差值≥3000）
  3. Agent生成澄清提示："你之前预算偏好是5000元，这次是10000元。本次按哪个预算执行？"
  4. 用户回复"按最新的"，Agent更新 budget_hint=10000，冲突标记为已解决

冲突检测规则：
  - 预算冲突（budget_hint）：新旧比值≥2 且 差值≥3000，严重级别 high
  - 天数冲突（days_hint）：新旧差值≥3天，严重级别 medium
  - 人数冲突（people_hint）：新旧差值≥2人，严重级别 medium
  - 季节冲突（season_hint）：新旧值不同，严重级别 low
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class MemoryConflictResolutionHelper:
    """【核心】偏好冲突检测、澄清提示生成和解决追踪的辅助类。

    本类封装了记忆冲突处理的完整生命周期：
      1. 检测冲突（detect_preference_conflict）
      2. 记录冲突（record_conflict）
      3. 生成澄清提示（build_conflict_clarification_hint / consume_conflict_clarification_hint）
      4. 识别用户解决意图（extract_conflict_resolution_intent）
      5. 解决冲突（resolve_pending_clarifications）
      6. 审计日志（append_conflict_resolution_log）

    本类绑定到 MemoryManager 实例，通过 _manager 访问共享状态和方法。
    """

    def __init__(self, manager: Any):
        """绑定到所属的 MemoryManager 实例。

        Args:
            manager: MemoryManager 实例，提供 _sync_lock、_sessions、_normalize_profile 等共享状态
        """
        self._manager = manager

    def build_clarification_turn_fingerprint(self, user_message: str, query_tokens: set[str]) -> str:
        """为当前对话轮次构建稳定的指纹，用于澄清重试去重。

        指纹的作用：同一轮对话中，多次调用澄清辅助方法不会重复计数重试次数。
        不同轮次的相同问题才会递增重试计数。

        策略：优先使用查询token的排序拼接，若token为空则使用原始消息文本。

        Args:
            user_message: 用户原始消息
            query_tokens: 从用户消息中提取的关键词token集合

        Returns:
            轮次指纹字符串，如 "query_tokens:成都 预算 3天" 或 "query_text:我想去成都玩3天"
        """
        normalized = " ".join(sorted(token for token in query_tokens if token))
        if normalized:
            return f"query_tokens:{normalized[:128]}"
        short = (user_message or "").strip().lower().replace("\n", " ")
        return f"query_text:{short[:128]}"

    def consume_conflict_clarification_hint(
        self,
        session_id: str,
        query_tokens: set[str],
        turn_fingerprint: str,
    ) -> str:
        """【核心】消费当前轮次可用的待澄清项，并更新重试状态。

        与 build_conflict_clarification_hint 的区别：
          - 本方法会修改待澄清项的重试计数和询问时间（有副作用）
          - build 方法是纯计算，不修改状态

        评分公式：score = severity_weight × 1.5 + overlap × 2 + recency
          - severity_weight：严重级别权重（high=3, medium=2, low=1）
          - overlap：待澄清项关键词与用户查询token的交集大小
          - recency：位置权重（越靠后越新，值越大）

        Args:
            session_id: 会话ID
            query_tokens: 当前查询的token集合
            turn_fingerprint: 当前轮次指纹（用于去重计数）

        Returns:
            澄清提示文本，无待澄清项时返回空字符串
        """
        manager = self._manager
        with manager._sync_lock:  # 线程安全：加锁访问共享状态
            session = manager._sessions.get(session_id)
            if not session:
                return ""
            profile = manager._normalize_profile(session.get("profile", {}))
            session["profile"] = profile
            pending = profile.get("pending_clarifications", [])
            if not isinstance(pending, list) or not pending:
                return ""

            # 对所有待澄清项评分排序
            scored: List[tuple[float, Dict[str, Any], str]] = []
            total = max(1, len(pending))
            for idx, item in enumerate(pending):
                if not isinstance(item, dict):
                    continue
                if str(item.get("state", "pending")).lower() != "pending":
                    continue
                retry_count = manager._safe_int(item.get("retry_count", 0) or 0)
                last_fingerprint = str(item.get("last_asked_fingerprint", "")).strip()
                # 超过最大重试次数且不是当前轮次，跳过
                if retry_count >= manager.CLARIFICATION_MAX_ASK_PER_ITEM and last_fingerprint != turn_fingerprint:
                    continue
                prompt = str(item.get("prompt", "")).strip()
                if not prompt:
                    continue
                severity = str(item.get("severity", "medium")).lower()
                severity_weight = manager.CLARIFICATION_SEVERITY_PRIORITY.get(severity, 2)
                # 计算关键词重叠度：待澄清项的关键词与用户查询token的交集
                focus_text = " ".join(
                    [
                        str(item.get("key", "")),
                        str(item.get("old_value", "")),
                        str(item.get("new_value", "")),
                        prompt,
                    ]
                )
                overlap = len(query_tokens & manager._tokenize(focus_text)) if query_tokens else 0
                recency = float(idx + 1) / float(total)  # 位置越靠后越新，权重越高
                score = float(severity_weight * 1.5) + float(overlap * 2) + recency
                scored.append((score, item, prompt))

            if not scored:
                return ""

            # 按评分降序排列，取前 CLARIFICATION_TOP_K 个
            scored.sort(key=lambda item: (item[0], item[2]), reverse=True)
            now = datetime.now().isoformat()
            prompts: List[str] = []
            seen: set[str] = set()
            for _, item, prompt in scored:
                if prompt in seen:
                    continue
                last_fingerprint = str(item.get("last_asked_fingerprint", "")).strip()
                if last_fingerprint != turn_fingerprint:
                    # 重试计数按轮次递增：同一轮多次调用不重复计数
                    item["retry_count"] = manager._safe_int(item.get("retry_count", 0) or 0) + 1
                    item["asked_at"] = now
                    item["last_asked_fingerprint"] = turn_fingerprint
                    manager._increment_profile_stat(profile, "clarification_asked", 1)
                prompts.append(prompt)
                seen.add(prompt)
                if len(prompts) >= manager.CLARIFICATION_TOP_K:
                    break

            return self.compose_conflict_clarification_hint(prompts)

    def build_conflict_clarification_hint(self, profile: Dict[str, Any], query_tokens: set[str]) -> str:
        """对待澄清的偏好冲突进行评分排序，生成确定性的澄清提示。

        与 consume 方法的区别：本方法是纯计算，不修改 profile 状态，
        适用于只读场景（如预览将要展示的澄清提示）。

        Args:
            profile: 用户偏好档案
            query_tokens: 当前查询的token集合

        Returns:
            澄清提示文本
        """
        manager = self._manager
        if not isinstance(profile, dict):
            return ""

        pending = profile.get("pending_clarifications", [])
        if not isinstance(pending, list) or not pending:
            return ""

        scored: List[tuple[float, str]] = []
        total = max(1, len(pending))
        for idx, item in enumerate(pending):
            if not isinstance(item, dict):
                continue
            if str(item.get("state", "pending")).lower() != "pending":
                continue
            retry_count = manager._safe_int(item.get("retry_count", 0) or 0)
            if retry_count >= manager.CLARIFICATION_MAX_ASK_PER_ITEM:
                continue
            prompt = str(item.get("prompt", "")).strip()
            if not prompt:
                continue
            severity = str(item.get("severity", "medium")).lower()
            severity_weight = manager.CLARIFICATION_SEVERITY_PRIORITY.get(severity, 2)
            focus_text = " ".join(
                [
                    str(item.get("key", "")),
                    str(item.get("old_value", "")),
                    str(item.get("new_value", "")),
                    prompt,
                ]
            )
            overlap = len(query_tokens & manager._tokenize(focus_text)) if query_tokens else 0
            recency = float(idx + 1) / float(total)
            score = float(severity_weight * 1.5) + float(overlap * 2) + recency
            scored.append((score, prompt))

        if not scored:
            return ""

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        prompts: List[str] = []
        seen: set[str] = set()
        for _, prompt in scored:
            if prompt in seen:
                continue
            prompts.append(prompt)
            seen.add(prompt)
            if len(prompts) >= manager.CLARIFICATION_TOP_K:
                break

        if not prompts:
            return ""
        return self.compose_conflict_clarification_hint(prompts)

    @staticmethod
    def compose_conflict_clarification_hint(prompts: List[str]) -> str:
        """将多个澄清提示组合为最终的辅助文本，供Agent运行时展示。

        格式示例：
          偏好冲突自动澄清:
          - 你之前预算偏好是5000元，这次是10000元。本次按哪个预算执行？
          - 你之前常用天数是5天，这次是3天。按哪一个规划？
          请先用1句确认冲突偏好，再继续提供可执行建议；若用户本轮已明确选择，则直接按最新选择执行。

        Args:
            prompts: 澄清提示列表

        Returns:
            组合后的澄清提示文本
        """
        if not prompts:
            return ""
        return (
            "偏好冲突自动澄清:\n- "
            + "\n- ".join(prompts)
            + "\n请先用 1 句确认冲突偏好，再继续提供可执行建议；若用户本轮已明确选择，则直接按最新选择执行。"
        )

    def extract_conflict_resolution_intent(self, text: str) -> Dict[str, Any]:
        """【核心】检测用户文本中是否包含明确的冲突解决意图。

        当用户说"按最新的"、"以这次为准"等表达时，识别为解决意图，
        Agent可直接更新偏好而无需再次确认。

        解决意图标记词：
          - 通用标记：为准、按这次、以这次、按最新、以最新、就按、本次按、这次按
          - 全局覆盖标记：按最新、以最新、按这次、以这次、本次按、这次按
            （触发 force_all=True，所有冲突偏好都用新值覆盖）

        偏好键识别：
          - budget_hint：预算相关词（预算/花费/开销/元/人民币等）
          - days_hint：天数相关词（3天/5日/天数/行程天数等）
          - people_hint：人数相关词（2人/3位/人数/同行等）
          - season_hint：季节相关词（季节/月份/春夏秋冬/暑假等）

        Args:
            text: 用户消息文本

        Returns:
            {"force_all": bool, "keys": set} — force_all表示全部覆盖，keys表示具体涉及的偏好键
        """
        markers = ["为准", "按这次", "以这次", "按最新", "以最新", "就按", "本次按", "这次按"]
        force_all_markers = ["按最新", "以最新", "按这次", "以这次", "本次按", "这次按"]
        has_resolution_marker = any(marker in text for marker in markers)
        if not has_resolution_marker:
            return {"force_all": False, "keys": set()}

        keys: set[str] = set()
        # 识别预算相关关键词
        if any(word in text for word in ["预算", "花费", "开销", "元", "人民币", "rmb", "cny"]):
            keys.add("budget_hint")
        # 识别天数相关关键词（如"3天"、"5日"）
        if re.search(r"\d{1,2}\s*(天|日)", text) or any(word in text for word in ["天数", "行程天数", "日程"]):
            keys.add("days_hint")
        # 识别人数相关关键词（如"2人"、"3位"）
        if re.search(r"\d{1,2}\s*(人|位)", text) or any(word in text for word in ["人数", "同行", "大人", "小孩"]):
            keys.add("people_hint")
        # 识别季节相关关键词
        if any(word in text for word in ["季节", "月份", "春", "夏", "秋", "冬", "暑假", "寒假"]):
            keys.add("season_hint")

        return {"force_all": any(marker in text for marker in force_all_markers), "keys": keys}

    @staticmethod
    def should_force_replace_for_key(key: str, resolution_intent: Dict[str, Any]) -> bool:
        """判断某个偏好键是否应该强制用新值替换。

        判断逻辑：
          1. 若 force_all=True（用户说了"按最新"等全局覆盖词），则所有键都强制替换
          2. 若 force_all=False，则只替换用户明确提到的键（keys 集合中的键）

        Args:
            key: 偏好键名，如 "budget_hint"
            resolution_intent: extract_conflict_resolution_intent 的返回值

        Returns:
            True 表示该键应强制用新值替换
        """
        force_all = bool(resolution_intent.get("force_all"))
        keyed = resolution_intent.get("keys", set())
        if not isinstance(keyed, set):
            keyed = set()
        return force_all or key in keyed

    def resolve_pending_clarifications(
        self,
        profile: Dict[str, Any],
        key: str,
        now: str,
        resolution_source: str,
        new_value: Any,
        default_old_value: Any = None,
    ) -> None:
        """【核心】解决指定键的待澄清项，并持久化解决记录。

        流程：
          1. 遍历 pending_clarifications，找到匹配 key 且状态为 pending 的项
          2. 将这些项的状态改为 "resolved"，记录解决时间和来源
          3. 从 pending_clarifications 中移除已解决的项
          4. 在 conflict_log 中标记对应的冲突条目为已解决
          5. 追加冲突解决审计日志

        Args:
            profile: 用户偏好档案
            key: 被解决的偏好键，如 "budget_hint"
            now: 当前时间（ISO格式）
            resolution_source: 解决来源，如 "user_explicit"（用户明确选择）
            new_value: 新的偏好值
            default_old_value: 旧值的默认回退
        """
        manager = self._manager
        pending = profile.get("pending_clarifications", [])
        if not isinstance(pending, list) or not pending:
            return

        remaining: List[Any] = []
        resolved_entries: List[Dict[str, Any]] = []
        for item in pending:
            if not isinstance(item, dict):
                remaining.append(item)
                continue
            if item.get("key") != key:
                remaining.append(item)
                continue
            state = str(item.get("state", "pending")).lower()
            if state == "resolved":
                continue  # 已解决的项直接丢弃
            item["state"] = "resolved"
            item["resolved_at"] = now
            item["resolution_source"] = resolution_source
            resolved_entries.append(dict(item))
        profile["pending_clarifications"] = remaining

        if not resolved_entries:
            return

        # 标记冲突日志中对应的条目为已解决
        self.mark_conflict_log_resolved(
            profile=profile,
            key=key,
            now=now,
            resolution_source=resolution_source,
            resolved_value=new_value,
        )
        # 追加审计日志
        for item in resolved_entries:
            self.append_conflict_resolution_log(
                profile=profile,
                key=key,
                old_value=item.get("old_value", default_old_value),
                new_value=new_value,
                now=now,
                resolution_source=resolution_source,
                retry_count=manager._safe_int(item.get("retry_count", 0) or 0),
                asked_at=item.get("asked_at"),
            )
        manager._increment_profile_stat(profile, "conflict_resolved", len(resolved_entries))

    def mark_conflict_log_resolved(
        self,
        profile: Dict[str, Any],
        key: str,
        now: str,
        resolution_source: str,
        resolved_value: Any,
    ) -> None:
        """在冲突日志中标记最新一条未解决的冲突为已解决。

        从后往前遍历 conflict_log，找到匹配 key 且未解决的最新条目并标记。
        只标记一条（最新的），因为同一 key 可能有多条冲突记录。

        Args:
            profile: 用户偏好档案
            key: 偏好键
            now: 解决时间
            resolution_source: 解决来源
            resolved_value: 最终采用的值
        """
        conflict_log = profile.get("conflict_log", [])
        if not isinstance(conflict_log, list) or not conflict_log:
            return
        for entry in reversed(conflict_log):  # 从后往前找最新的
            if not isinstance(entry, dict):
                continue
            if entry.get("key") != key:
                continue
            if str(entry.get("state", "pending")).lower() == "resolved":
                continue
            if str(entry.get("type")) == "conflict_resolved":
                continue  # 跳过已解决的审计记录
            entry["state"] = "resolved"
            entry["resolved_at"] = now
            entry["resolution_source"] = resolution_source
            entry["resolved_value"] = resolved_value
            return

    def append_conflict_resolution_log(
        self,
        profile: Dict[str, Any],
        key: str,
        old_value: Any,
        new_value: Any,
        now: str,
        resolution_source: str,
        retry_count: int = 0,
        asked_at: Optional[str] = None,
    ) -> None:
        """追加一条冲突解决审计记录，用于可追溯性。

        审计记录包含完整的冲突生命周期信息：
          - 旧值/新值/解决时间/解决来源/重试次数/首次询问时间

        日志上限50条，超出时保留最新的50条。

        Args:
            profile: 用户偏好档案
            key: 偏好键
            old_value: 旧偏好值
            new_value: 新偏好值
            now: 解决时间
            resolution_source: 解决来源
            retry_count: 重试次数（Agent问了几次才得到用户确认）
            asked_at: 首次询问时间
        """
        manager = self._manager
        conflict_log = profile.setdefault("conflict_log", [])
        if not isinstance(conflict_log, list):
            profile["conflict_log"] = []
            conflict_log = profile["conflict_log"]
        conflict_log.append(
            {
                "key": key,                              # 偏好键
                "type": "conflict_resolved",              # 记录类型：冲突已解决
                "old_value": old_value,                   # 旧值
                "new_value": new_value,                   # 新值
                "severity": "info",                       # 解决记录的严重级别为info
                "prompt": None,                           # 解决记录无需提示
                "created_at": now,                        # 创建时间
                "state": "resolved",                      # 状态：已解决
                "asked_at": asked_at,                     # 首次询问时间
                "retry_count": max(0, manager._safe_int(retry_count)),  # 重试次数
                "resolved_at": now,                       # 解决时间
                "resolution_source": resolution_source,   # 解决来源
            }
        )
        # 日志上限50条，超出时截断保留最新的50条
        if len(conflict_log) > 50:
            del conflict_log[:-50]

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """安全地将值转换为整数，转换失败时返回默认值。

        用于处理从JSON反序列化后可能为字符串或None的数字字段。

        Args:
            value: 待转换的值
            default: 转换失败时的默认值

        Returns:
            转换后的整数
        """
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def normalize_conflict_entry(cls, item: Any) -> Optional[Dict[str, Any]]:
        """将一条冲突日志条目归一化为标准的持久化格式。

        归一化确保从磁盘加载的数据结构一致，避免因版本升级导致字段缺失。

        Args:
            item: 原始冲突条目（可能来自JSON反序列化）

        Returns:
            归一化后的字典，输入无效时返回 None
        """
        if not isinstance(item, dict):
            return None
        retry_count = cls._safe_int(item.get("retry_count", 0) or 0)
        state = str(item.get("state", "pending")).lower()
        if state not in {"pending", "resolved"}:
            state = "pending"  # 非法状态归一化为 pending
        return {
            "key": item.get("key"),                          # 偏好键
            "type": item.get("type"),                        # 冲突类型
            "old_value": item.get("old_value"),              # 旧值
            "new_value": item.get("new_value"),              # 新值
            "severity": item.get("severity", "medium"),      # 严重级别
            "prompt": item.get("prompt"),                    # 澄清提示
            "created_at": item.get("created_at", datetime.now().isoformat()),  # 创建时间
            "state": state,                                  # 状态（pending/resolved）
            "asked_at": item.get("asked_at"),                # 首次询问时间
            "retry_count": max(0, retry_count),              # 重试次数
            "resolved_at": item.get("resolved_at"),          # 解决时间
            "resolution_source": item.get("resolution_source"),  # 解决来源
            "resolved_value": item.get("resolved_value"),    # 最终采用的值
        }

    @classmethod
    def normalize_pending_clarification(cls, item: Any) -> Optional[Dict[str, Any]]:
        """归一化一条待澄清条目，保留重试指纹状态。

        与 normalize_conflict_entry 的区别：
          - 额外保留 last_asked_fingerprint 字段（用于去重计数）
          - 已解决的条目返回 None（不应出现在待澄清队列中）

        Args:
            item: 原始待澄清条目

        Returns:
            归一化后的字典，已解决或无效时返回 None
        """
        normalized = cls.normalize_conflict_entry(item)
        if normalized is None:
            return None
        normalized["last_asked_fingerprint"] = (
            item.get("last_asked_fingerprint") if isinstance(item, dict) else None
        )
        # 已解决的条目不应出现在待澄清队列中
        if str(normalized.get("state", "pending")).lower() == "resolved":
            return None
        return normalized

    def detect_preference_conflict(
        self,
        key: str,
        existing: Dict[str, Any],
        new_value: Any,
        new_source: str,
    ) -> Optional[Dict[str, Any]]:
        """【核心】检测偏好冲突，若检测到冲突则返回冲突描述。

        冲突检测规则：
          - budget_hint：新旧比值≥2 且 差值≥3000元 → high 严重级别
            例：之前5000元，现在10000元（2倍 + 差值5000≥3000）
          - days_hint：新旧差值≥3天 → medium 严重级别
            例：之前5天，现在3天（差值2<3，不冲突）；之前7天，现在3天（差值4≥3，冲突）
          - people_hint：新旧差值≥2人 → medium 严重级别
            例：之前4人，现在2人（差值2≥2，冲突）
          - season_hint：新旧值不同 → low 严重级别
            例：之前"夏季"，现在"冬季"

        Args:
            key: 偏好键名
            existing: 已存储的偏好条目 {"value": ..., ...}
            new_value: 新的偏好值
            new_source: 新值的来源标识

        Returns:
            冲突描述字典（含 type/old_value/new_value/severity/prompt），无冲突返回 None
        """
        manager = self._manager
        old_value = existing.get("value")
        if old_value is None:
            return None

        # ---- 预算冲突检测 ----
        if key == "budget_hint":
            old_num = manager._to_number(old_value)
            new_num = manager._to_number(new_value)
            if old_num and new_num:
                ratio = max(old_num, new_num) / max(1.0, min(old_num, new_num))
                if ratio >= 2.0 and abs(old_num - new_num) >= 3000:
                    return {
                        "type": "budget_conflict",
                        "old_value": old_value,
                        "new_value": new_value,
                        "severity": "high",  # 预算冲突严重级别最高
                        "prompt": f"你之前预算偏好是 {old_value}，这次是 {new_value}。本次按哪个预算执行？",
                        "new_source": new_source,
                    }

        # ---- 天数冲突检测 ----
        if key == "days_hint":
            old_num = manager._to_number(old_value)
            new_num = manager._to_number(new_value)
            if old_num is not None and new_num is not None and abs(old_num - new_num) >= 3:
                return {
                    "type": "days_conflict",
                    "old_value": old_value,
                    "new_value": new_value,
                    "severity": "medium",
                    "prompt": f"你之前常用天数是 {int(old_num)} 天，这次是 {int(new_num)} 天。按哪一个规划？",
                    "new_source": new_source,
                }

        # ---- 人数冲突检测 ----
        if key == "people_hint":
            old_num = manager._to_number(old_value)
            new_num = manager._to_number(new_value)
            if old_num is not None and new_num is not None and abs(old_num - new_num) >= 2:
                return {
                    "type": "people_conflict",
                    "old_value": old_value,
                    "new_value": new_value,
                    "severity": "medium",
                    "prompt": f"你之前出行人数偏好是 {int(old_num)} 人，这次是 {int(new_num)} 人。本次按哪个人数？",
                    "new_source": new_source,
                }

        # ---- 季节冲突检测 ----
        if key == "season_hint" and str(old_value).strip() != str(new_value).strip():
            return {
                "type": "season_conflict",
                "old_value": old_value,
                "new_value": new_value,
                "severity": "low",  # 季节冲突严重级别最低
                "prompt": f"你之前季节偏好是 {old_value}，这次是 {new_value}。本次按哪个季节建议？",
                "new_source": new_source,
            }
        return None

    def record_conflict(self, profile: Dict[str, Any], key: str, conflict: Dict[str, Any], now: str) -> None:
        """【核心】将一个偏好冲突记录到审计日志和待澄清队列。

        双写策略：
          1. 写入 conflict_log（审计日志，记录所有冲突事件，上限50条）
          2. 写入 pending_clarifications（待澄清队列，等待用户确认，上限10条）

        对于同一 key 的待澄清项，采用更新策略（而非追加），
        确保同一偏好键只有一个待澄清项。

        Args:
            profile: 用户偏好档案
            key: 偏好键名
            conflict: detect_preference_conflict 返回的冲突描述
            now: 当前时间
        """
        entry = {
            "key": key,                              # 偏好键
            "type": conflict.get("type"),            # 冲突类型
            "old_value": conflict.get("old_value"),  # 旧值
            "new_value": conflict.get("new_value"),  # 新值
            "severity": conflict.get("severity", "medium"),  # 严重级别
            "prompt": conflict.get("prompt"),        # 澄清提示
            "created_at": now,                       # 创建时间
            "state": "pending",                      # 初始状态：待处理
            "asked_at": None,                        # 首次询问时间（尚未询问）
            "retry_count": 0,                        # 重试次数
            "resolved_at": None,                     # 解决时间（尚未解决）
            "resolution_source": None,               # 解决来源（尚未解决）
            "last_asked_fingerprint": None,           # 上次询问的轮次指纹
        }

        # ---- 写入审计日志 ----
        conflict_log = profile.setdefault("conflict_log", [])
        conflict_log.append(entry)
        if len(conflict_log) > 50:
            del conflict_log[:-50]

        # ---- 写入待澄清队列 ----
        pending = profile.setdefault("pending_clarifications", [])
        # 查找同一 key 的已有待澄清项
        same_key_pending = next(
            (
                item
                for item in pending
                if isinstance(item, dict)
                and item.get("key") == key
                and str(item.get("state", "pending")).lower() == "pending"
            ),
            None,
        )
        if same_key_pending is None:
            # 无同 key 项，直接追加
            pending.append(dict(entry))
        else:
            # 有同 key 项，更新其内容（保留重试计数等状态）
            same_key_pending["type"] = entry["type"]
            same_key_pending["old_value"] = entry["old_value"]
            same_key_pending["new_value"] = entry["new_value"]
            same_key_pending["severity"] = entry["severity"]
            same_key_pending["prompt"] = entry["prompt"]
            same_key_pending["created_at"] = entry["created_at"]
            same_key_pending["state"] = "pending"
        # 待澄清队列上限10条
        if len(pending) > 10:
            del pending[:-10]
