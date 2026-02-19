"""
工具版本管理器

提供工具版本管理、回滚和兼容性检查功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import semver

logger = logging.getLogger(__name__)


@dataclass
class ToolVersion:
    """工具版本"""
    version: str
    tool_id: str
    changes: str = ""
    breaking: bool = False
    created_at: str = ""
    deprecated: bool = False


class ToolVersionManager:
    """工具版本管理器"""

    def __init__(self):
        self._versions: Dict[str, List[ToolVersion]] = {}
        logger.info("ToolVersionManager initialized")

    def register_version(
        self,
        tool_id: str,
        version: str,
        changes: str = "",
        is_breaking: bool = False
    ) -> ToolVersion:
        """注册新版本"""
        if tool_id not in self._versions:
            self._versions[tool_id] = []

        ver = ToolVersion(
            version=version,
            tool_id=tool_id,
            changes=changes,
            breaking=is_breaking,
            created_at=datetime.now().isoformat()
        )

        self._versions[tool_id].append(ver)
        logger.info(f"Registered version {version} for tool {tool_id}")
        return ver

    def get_latest_version(self, tool_id: str) -> Optional[ToolVersion]:
        """获取最新版本"""
        versions = self._versions.get(tool_id, [])
        if not versions:
            return None
        return max(versions, key=lambda v: semver.VersionInfo.parse(v.version))

    def is_compatible(self, tool_id: str, version1: str, version2: str) -> bool:
        """检查版本兼容性"""
        v1 = semver.VersionInfo.parse(version1)
        v2 = semver.VersionInfo.parse(version2)

        # 相同主版本兼容
        return v1.major == v2.major

    def deprecate_version(self, tool_id: str, version: str):
        """废弃版本"""
        for v in self._versions.get(tool_id, []):
            if v.version == version:
                v.deprecated = True
                logger.warning(f"Deprecated {tool_id} version {version}")


class ToolDependencyResolver:
    """工具依赖解析器"""

    def __init__(self):
        self._dependencies: Dict[str, List[str]] = {}
        logger.info("ToolDependencyResolver initialized")

    def register_dependency(self, tool_id: str, depends_on: List[str]):
        """注册依赖"""
        self._dependencies[tool_id] = depends_on

    def resolve(self, tool_id: str) -> List[str]:
        """解析依赖顺序"""
        visited = set()
        result = []

        def visit(tid: str):
            if tid in visited:
                return
            visited.add(tid)
            for dep in self._dependencies.get(tid, []):
                visit(dep)
            result.append(tid)

        visit(tool_id)
        return result

    def check_circular(self, tool_id: str) -> bool:
        """检查循环依赖"""
        visited = set()
        rec_stack = set()

        def visit(tid: str) -> bool:
            visited.add(tid)
            rec_stack.add(tid)

            for dep in self._dependencies.get(tid, []):
                if dep not in visited:
                    if visit(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(tid)
            return False

        return visit(tool_id)


class ToolMetricsCollector:
    """工具指标收集器"""

    def __init__(self):
        self._metrics: Dict[str, Dict] = {}
        logger.info("ToolMetricsCollector initialized")

    def record_call(self, tool_id: str, success: bool, duration: float):
        """记录调用"""
        if tool_id not in self._metrics:
            self._metrics[tool_id] = {
                "total_calls": 0,
                "success_calls": 0,
                "total_duration": 0.0,
                "failures": 0
            }

        m = self._metrics[tool_id]
        m["total_calls"] += 1
        m["total_duration"] += duration
        if success:
            m["success_calls"] += 1
        else:
            m["failures"] += 1

    def get_stats(self, tool_id: str) -> Dict:
        """获取统计"""
        m = self._metrics.get(tool_id, {})
        if not m:
            return {}

        total = m.get("total_calls", 0)
        success = m.get("success_calls", 0)

        return {
            "total_calls": total,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration": m.get("total_duration", 0) / total if total > 0 else 0,
            "failures": m.get("failures", 0)
        }
