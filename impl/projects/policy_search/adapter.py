"""policy_search 项目的 Adapter（scaffold 生成，待填充）。

继承 ProjectAdapter（来自 impl.core.adapter_v2），只做加载和暴露，不承载业务逻辑。
合规检查要求：adapter 只允许 _load_* 方法，禁止业务方法（build_*/normalize_* 等）。
"""
from __future__ import annotations

from impl.core.adapter_v2 import ProjectAdapter


class Adapter(ProjectAdapter):
    """只负责加载 Policy Search 的四个项目角色。"""

    metadata_fields = set()

    def _load_attribute(self):
        from impl.projects.policy_search.attribute import PolicySearchAttribute
        return PolicySearchAttribute(self.spec)

    def _load_judge(self):
        from impl.projects.policy_search.judge import PolicySearchJudge
        return PolicySearchJudge(self.spec)

    def _load_live(self):
        from impl.projects.policy_search.live import PolicySearchLive
        return PolicySearchLive(self.spec)

    def _load_mock(self):
        from impl.projects.policy_search.mock import PolicySearchMock
        return PolicySearchMock(self.spec)
