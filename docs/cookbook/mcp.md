# MCP
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 可以把工具部署成独立服务。`mcp_toolset` 会把远端工具翻成本地 `Tool` 子类。

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

- 进入上下文：建立连接，调用 `initialize` 和 `tools/list`，返回 `Tool` 子类列表
- 退出上下文：关连接

## 混合注册
本地工具和 MCP 工具可以放进同一个判别式联合：
```python
async with mcp_toolset(server) as remote_tools:
    Tools = Union[LocalTool, *remote_tools]
    class Action(BaseModel):
        action: Annotated[Tools, Field(discriminator="kind")]
```

## 传输方式

- **stdio**：MCP server 作为子进程运行，走 stdin / stdout

  ```python
  StdioMCP(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])

  ```

- **Streamable HTTP**（MCP 2024-11-05）：走 HTTP，兼容 JSON / SSE 响应体，使用 `Mcp-Session-Id` 追踪会话

  ```python
  HttpMCP(url="https://mcp.example.com/")

  ```
两种传输都配置在 `MCPServer` 里，由 `mcp_toolset` 建立连接。

## 对接 FastMCP
`HttpMCP` 对齐 MCP 2024-11-05 Streamable HTTP 规范，可以连接 FastMCP server（官方 `mcp.server.fastmcp` 或独立 `fastmcp` 包）。

## 不覆盖的范围

- 老的 SSE 传输（`GET /sse` 长连接那种）
- resources / prompts / sampling
- 全局 registry · 断线重连 · schema 动态刷新 · `ToolSet` 抽象 protocol
这些能力可以直接使用官方 MCP SDK。

---

- 可跑示例：[examples/mcp_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/mcp_tool_use.py) · [examples/_mcp_demo_server.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/_mcp_demo_server.py)
- 完整签名：[API：pyxis.mcp](../api/mcp.md)
