"""资源与引用（spec/alg/resources.md，P1 离线试点）：地址、规范文本、资源类型、挂载、引用核对。

资源的描述、模板与读取结果用 MCP 的数据结构（``mcp.types``）；规范文本的区间、引用核对、角色是在其上的扩展。

试点期只被离线脚本与测试使用，现有评测路径不引用本包。
"""
from .cite import CiteResult, Region, cite
from .mount import ResourceTable
from .mount import DIRECTORY
from .spec import META_PREFIX, Address, Block
from .types import TYPES
from .types.record_set import Role

__all__ = ["Address", "Block", "CiteResult", "DIRECTORY", "META_PREFIX", "Region", "ResourceTable", "Role", "TYPES", "cite"]
