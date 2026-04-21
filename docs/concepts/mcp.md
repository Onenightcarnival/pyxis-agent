# MCP 适配

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 让你把工具部署
成独立服务，pyxis 通过适配层把远端工具**翻译成本地 `Tool` 子类**——用起来
跟自己定义的工具没区别。

## 最小例子

```python
from pyxis import mcp_toolset
from pyxis.mcp import StdioMCP, HttpMCP

server = StdioMCP(command="python", args=["-m", "my_mcp_server"])
# 或：server = HttpMCP(url="https://mcp.example.com/")

async with mcp_toolset(server) as tools:
    # tools 是一个 list[type[Tool]]，远端每个工具翻成一个 Tool 子类
    print([T.__name__ for T in tools])
```

进入上下文时：建立连接 → `initialize` → `tools/list` → 翻译 schema → 给你
`Tool` 子类。退出时关连接。

## 混合注册 = 拼 list

本地工具和 MCP 工具在 pyxis 眼里没区别。进判别式联合就是拼个 list：

```python
class Action(BaseModel):
    action: Annotated[
        NativeSearchWeb | McpTool1 | McpTool2,
        Field(discriminator="kind"),
    ]
```

运行时：

```python
async with mcp_toolset(server) as remote_tools:
    Tools = Union[LocalTool, *remote_tools]     # 动态判别式
    ...
```

## 传输方式

- **stdio**：把 MCP server 作为子进程启动，走 stdin/stdout
  ```python
  StdioMCP(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
  ```
- **Streamable HTTP**（MCP 2024-11-05 规范）：真 HTTP 调用，兼容 JSON 或
  SSE 响应体，跨请求靠 `Mcp-Session-Id` 追踪会话
  ```python
  HttpMCP(url="https://mcp.example.com/")
  ```

两者都是 `MCPServer` 判别式联合的成员，是**数据**（没有 `run()`）；
`mcp_toolset` 负责跑起来。

## 直接对接 FastMCP

`HttpMCP` 对齐 MCP 2024-11-05 Streamable HTTP 规范。这意味着**可以直接对接
FastMCP 写的 server**——不管是官方 `mcp.server.fastmcp` 还是独立 `fastmcp`
包。不需要写适配代码。

## 故意不做的事

- **不做** `arun`（已经用 async context manager，没必要再多一层）
- **不做** 老的 SSE 传输（`GET /sse` 长连接那种）
- **不做** resources / prompts / sampling（pyxis 只关心 tools）
- **不做** 全局 registry、断线重连、schema 动态刷新
- **不做** `ToolSet` 抽象 protocol——list 就够了

这些不是"以后会做"，是**哲学决定不做**。需要这些特性，直接用官方 MCP SDK。

完整签名看 [API 参考 → pyxis.mcp](../api/mcp.md)；可视化 demo 在仓库的 `apps/mcp-demo/`。
