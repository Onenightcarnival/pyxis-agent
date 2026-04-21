# MCP 适配

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 让你把工具部署成独立服务。pyxis 的适配层把远端工具翻成本地 `Tool` 子类，用起来和自己定义的工具一样。

## 最小例子

```python
from pyxis import mcp_toolset
from pyxis.mcp import MCPServer, StdioMCP, HttpMCP

server = MCPServer(
    name="fs",
    transport=StdioMCP(command="python", args=["-m", "my_mcp_server"]),
    # 或 transport=HttpMCP(url="https://mcp.example.com/"),
)

async with mcp_toolset(server) as tools:
    # tools: list[type[Tool]]，远端每个工具对应一个 Tool 子类
    print([T.__name__ for T in tools])
```

- 进入上下文：建立连接 → `initialize` → `tools/list` → 翻译 schema → 返回 `Tool` 子类列表
- 退出上下文：关连接

## 混合注册 = 拼 list

本地工具和 MCP 工具形态一致，直接拼进判别式联合：

```python
async with mcp_toolset(server) as remote_tools:
    Tools = Union[LocalTool, *remote_tools]

    class Action(BaseModel):
        action: Annotated[Tools, Field(discriminator="kind")]
```

## 传输方式

- **stdio** — MCP server 起子进程，走 stdin / stdout
  ```python
  StdioMCP(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
  ```
- **Streamable HTTP**（MCP 2024-11-05 规范） — 真 HTTP，兼容 JSON / SSE 响应体，`Mcp-Session-Id` 追踪会话
  ```python
  HttpMCP(url="https://mcp.example.com/")
  ```

两者都是 `MCPServer` 判别式联合的成员 → 纯数据；`mcp_toolset` 负责跑起来。

## 对接 FastMCP

`HttpMCP` 对齐 MCP 2024-11-05 Streamable HTTP 规范，直接连 FastMCP 写的 server（官方 `mcp.server.fastmcp` 或独立 `fastmcp` 包）。无需适配代码。

## 故意不做

- 老的 SSE 传输（`GET /sse` 长连接那种）
- resources / prompts / sampling（pyxis 只关心 tools）
- 全局 registry · 断线重连 · schema 动态刷新 · `ToolSet` 抽象 protocol

要这些 → 用官方 MCP SDK。

---

- 可跑示例：[examples/mcp_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/mcp_tool_use.py) · [examples/_mcp_demo_server.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/_mcp_demo_server.py)
- 可视化：仓库的 [`apps/mcp-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
- 完整签名：[API → pyxis.mcp](../api/mcp.md)
