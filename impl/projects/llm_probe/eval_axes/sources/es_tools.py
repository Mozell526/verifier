"""受目录范围约束的 ES 工具和引用回读；mapping 决定字段，不预设知识库形状。"""
from __future__ import annotations

import json
from typing import Any

from impl.projects.llm_probe.material_tools import quote_in_text
from impl.tools.protocol import VerifiableTool, build_agno_tools
from .es_client import EsClient


def _fields(properties, prefix='', nested=False):
    result = []
    for name, spec in properties.items():
        path = prefix + name
        kind = spec.get('type', 'object')
        is_nested = nested or kind == 'nested'
        result.append({'name': path, 'type': kind, 'text_or_keyword': kind in ('text', 'keyword'),
                       'full_text': kind == 'text' and spec.get('index', True) and not is_nested,
                       'nested': is_nested})
        result.extend(_fields(spec.get('properties', {}), path + '.', is_nested))
        # multi-fields 不在 _source 中单独存在；明确给出回读用的源字段。
        for child in _fields(spec.get('fields', {}), path + '.', is_nested):
            child['source_field'] = path
            result.append(child)
    return result


def _project(value, field):
    if not field:
        return value
    if isinstance(value, list):
        return [_project(item, field) for item in value]
    if not isinstance(value, dict):
        raise ValueError(f'ES 字段不存在: {field}')
    if field in value:
        return value[field]
    head, _, tail = field.partition('.')
    if head not in value:
        raise ValueError(f'ES 字段不存在: {field}')
    return _project(value[head], tail)


def _text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class EsTools:
    def __init__(self, catalog, recorder, client=None):
        self.allowed = {item['uri'][len('es://'):] for item in catalog if item.get('source') == 'es'}
        self.recorder = recorder
        self.client = client or EsClient()

    def _guard(self, index):
        if index not in self.allowed:
            raise ValueError(f'index 必须是目录里的索引之一: {sorted(self.allowed)}')

    def _run(self, tool, index, args, action):
        receipt: dict[str, Any] = {'tool': tool, 'index': index, **args, 'returned_locators': []}
        try:
            self._guard(index)
            result = action()
            receipt['returned_locators'] = ([result['locator']] if 'locator' in result else
                                            [hit['locator'] for hit in result.get('hits', [])])
            return result
        except ValueError as exc:
            receipt['error'] = str(exc)
            return {'error': str(exc)}
        finally:
            self.recorder.append(receipt)

    def _outline(self, index):
        mapping = self.client.mapping(index)
        if index not in mapping:
            raise ValueError('ES 引用须为具体索引名')
        return {'index': index, 'fields': _fields(mapping[index]['mappings'].get('properties', {})),
                'doc_count': self.client.count(index)}

    def es_outline(self, index: str):
        return self._run('es_outline', index, {}, lambda: self._outline(index))

    def es_search(self, index: str, query: str, fields: list[str] | None = None):
        def action():
            if not query.strip():
                raise ValueError('query 不能为空')
            available = {f['name']: f for f in self._outline(index)['fields']}
            chosen = fields if fields is not None else [name for name, f in available.items() if f['full_text']]
            if not chosen or any(f not in available or not available[f]['text_or_keyword'] or available[f]['nested'] for f in chosen):
                raise ValueError('fields 必须是 mapping 中可检索的 text/keyword 字段；nested 字段需要 nested 查询，暂不支持')
            response = self.client.search(index, {
                'size': self.client.config.max_hits,
                'query': {'multi_match': {'query': query, 'fields': chosen}},
                'highlight': {'pre_tags': [''], 'post_tags': [''], 'fields': {f: {} for f in chosen}},
            })
            hits = []
            for hit in response.get('hits', {}).get('hits', [])[:self.client.config.max_hits]:
                for name, snippets in hit.get('highlight', {}).items():
                    if name not in chosen:
                        continue
                    text = '\n'.join(snippets)
                    hits.append({'locator': hit['_id'] + '#' + available[name].get('source_field', name),
                                 'score': hit.get('_score'), 'text': text[:self.client.config.max_field_chars],
                                 'truncated': len(text) > self.client.config.max_field_chars})
            return {'index': index, 'hits': hits}
        return self._run('es_search', index, {'query': query, 'fields': fields}, action)

    def es_read(self, index: str, locator: str):
        def action():
            doc_id, separator, field = locator.partition('#')
            if not doc_id or (separator and not field):
                raise ValueError('locator 必须为 <_id> 或 <_id>#<field>')
            source = self.client.get_doc(index, doc_id)
            text = _text(_project(source, field))
            limit = self.client.config.max_field_chars
            return {'index': index, 'locator': locator, 'text': text[:limit], 'truncated': len(text) > limit}
        return self._run('es_read', index, {'locator': locator}, action)

    def verify_quote(self, index, locator, quote):
        if '#' not in locator:
            return False
        result = self.es_read(index, locator)
        return 'error' not in result and quote_in_text(quote, result['text'])

    def tools(self):
        specs = [
            ('es_outline', self.es_outline, '查看目录中 ES 索引的 mapping 字段与文档数。', {}),
            ('es_search', self.es_search, 'multi_match 检索；缺省检索全部普通 text 字段，返回可回读 locator 与片段。',
             {'query': {'type': 'string', 'description': '检索词'}, 'fields': {'type': 'array', 'items': {'type': 'string'}, 'description': '可选：mapping 字段名'}}),
            ('es_read', self.es_read, '回读 ES 原文；字段 locator 为文档ID#字段路径，只有 ID 时返回整篇摘要。',
             {'locator': {'type': 'string', 'description': '工具返回的文档ID#字段路径'}}),
        ]
        return build_agno_tools([VerifiableTool(tool_id=name, description=description, execute_fn=fn,
            parameters={'type': 'object', 'properties': {'index': {'type': 'string', 'description': '目录里的具体索引名'}, **params},
                        'required': ['index'] + [key for key in params if key != 'fields']})
            for name, fn, description, params in specs])


def build_es_tools(catalog, recorder):
    return EsTools(catalog, recorder).tools() if catalog else []
