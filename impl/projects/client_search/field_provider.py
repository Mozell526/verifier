"""
client_search 项目专属：字段定义提供者实现。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from impl.core.schema import ProjectSpec

logger = logging.getLogger(__name__)


class ClientSearchFieldDefinitionProvider:
    """
    client_search 项目专属：从 YAML 文件加载字段定义。
    """

    def __init__(self, spec: ProjectSpec):
        self.spec = spec
        self._cached_data: Optional[dict] = None
        self._cached_behavior_data: Optional[dict] = None

    def _load_yaml(self) -> dict:
        """加载 field_definitions YAML 文件（带缓存）。"""
        if self._cached_data is not None:
            return self._cached_data

        field_def_path = self.spec.source_path("field_definitions")
        if not field_def_path:
            raise ValueError(f"Field definitions not configured for project {self.spec.project_id}")

        full_path = Path(field_def_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Field definitions file not found: {field_def_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            self._cached_data = yaml.safe_load(f)

        return self._cached_data

    def _load_behavior_yaml(self) -> Optional[dict]:
        """加载 behavior_intent_definitions YAML（可选，带缓存）。"""
        if self._cached_behavior_data is not None:
            return self._cached_behavior_data
        try:
            behavior_path = self.spec.source_path("behavior_intents")
        except Exception:
            behavior_path = ""
        if not behavior_path:
            self._cached_behavior_data = {}
            return self._cached_behavior_data
        full_path = Path(behavior_path)
        if not full_path.is_file():
            self._cached_behavior_data = {}
            return self._cached_behavior_data
        with open(full_path, 'r', encoding='utf-8') as f:
            self._cached_behavior_data = yaml.safe_load(f) or {}
        return self._cached_behavior_data

    def get_field_definition(self, field_name: str) -> Optional[dict]:
        """
        实现协议：从 YAML 中查找字段定义。

        client_search 项目的 YAML 格式：
        - 字段定义在 data['intents'] 列表中
        - 每个 intent 有 'field' 字段
        - 同一字段可能有多个 intent（不同操作符）
        """
        try:
            data = self._load_yaml()
            intents = data.get('intents', [])

            # 查找所有匹配的 intent
            field_entries = [item for item in intents if item.get('field') == field_name]

            if not field_entries:
                return self._get_behavior_field_definition(field_name)

            # 合并多个 intent 的信息
            operators = set()
            value_types = set()
            description = None
            examples = []
            enums = []
            unit = None
            notes = None

            for entry in field_entries:
                if entry.get('operator'):
                    operators.add(entry['operator'])
                if entry.get('value_type'):
                    value_types.add(entry['value_type'])
                if entry.get('description') and not description:
                    description = entry['description']
                if entry.get('examples'):
                    examples.extend(entry['examples'])
                if entry.get('enum') and not enums:
                    enums = entry['enum']
                if entry.get('unit') and not unit:
                    unit = entry['unit']
                if entry.get('notes') and not notes:
                    notes = entry['notes']

            # Context optimization: Only return minimal info for compact manifest
            # Full details available via tool on-demand
            result = {
                'field': field_name,
                'operators': sorted(operators),
                'value_types': sorted(value_types),
            }

            # Add optional fields only if non-empty and short
            if description and len(description) < 100:
                result['description'] = description
            if enums and len(enums) <= 5:  # Only very short enum lists
                result['enums'] = enums[:5]
            if unit:
                result['unit'] = unit

            return result

        except Exception as e:
            logger.error(f"Error loading field definition for {field_name}: {e}")
            return None

    def _get_behavior_field_definition(self, field_name: str) -> Optional[dict]:
        """field_definitions 未命中时，从 behavior_intent_definitions 的空间部分提供定义。"""
        try:
            data = self._load_behavior_yaml()
            if not isinstance(data, dict):
                return None
            if str(data.get("field") or "").strip() != field_name:
                return None
            intents = data.get("intents")
            if not isinstance(intents, list):
                return None
            supported = []
            unsupported = []
            for item in intents:
                if not isinstance(item, dict):
                    continue
                activity = str(item.get("activity") or "").strip()
                if not activity:
                    continue
                if item.get("is_supported") is False:
                    unsupported.append(activity)
                else:
                    supported.append(activity)
            if not supported and not unsupported:
                return None
            result = {
                'field': field_name,
                'operators': ['MATCH'],
                'value_types': ['enum'],
                'is_supported': bool(supported),
                'is_supported_explicit': True,
            }
            description = (
                "客户行为字段。空间部分来自 behavior_intent_definitions_args.yaml；"
                "aliases/activity_template/selection_notes/examples 属 current_behavior，不作为裁决依据。"
            )
            result['description'] = description[:100]
            enums = supported or unsupported
            if len(enums) <= 5:
                result['enums'] = enums[:5]
            return result
        except Exception as e:
            logger.error(f"Error loading behavior definition for {field_name}: {e}")
            return None
