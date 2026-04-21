# 概念

pyxis 的原语就这几个。每一页一个原语——最小例子 + 为什么这样设计 +
什么时候别用。都带可跑的 snippet，都指回对应的 API 参考。

## 建议阅读顺序

**第一次来**，按这四页读下去就够上手：

1. [哲学与定位](philosophy.md)——为什么只有这几个原语（5 分钟）。
2. [Step：code-as-prompt](step.md)——最小构件。理解这一页基本就理解了
   "函数即 prompt、字段顺序即思维链"。
3. [Flow：显式编排](flow.md)——多步调用怎么拼。
4. [Tool：action 即 schema](tool.md)——想让 LLM 选工具时看。

剩下三页**按需读**，不是主线：

- [human-in-the-loop](human.md)——只在要人类回应时读。
- [MCP 适配](mcp.md)——只在要接远端工具时读。
- [可观测性](observability.md)——生产部署前读一次：Langfuse 接入就一个
  import 的事。

最后一页 [Hook：观察者](hooks.md) 标了"进阶"——大多数人不需要碰。
看了 observability 还不够用（要自己接 Prometheus / OpenTelemetry /
Slack 告警）才进来。

## 速查

| 页 | 一句话 |
|---|---|
| [哲学与定位](philosophy.md)         | LLM 输出喂给代码不喂给人眼，四条约束随之而来 |
| [Step](step.md)                     | 函数 = prompt，Pydantic 字段顺序 = 思维链 |
| [Flow](flow.md)                     | 多步编排就是普通 Python 函数，不发明 DSL |
| [Tool](tool.md)                     | 工具 = `BaseModel + run()`，LLM 填判别式联合就是"选工具" |
| [human-in-the-loop](human.md)       | 生成器 `yield ask_human(...)` 挂起等答复 |
| [MCP 适配](mcp.md)                  | 远端 MCP 工具翻成本地 `Tool` 子类，混合注册 = 拼 list |
| [可观测性](observability.md)         | 生产接 Langfuse（换 import）；测试用 `trace()` + `FakeClient` |
| [Hook](hooks.md)（进阶）             | 自己接指标 / 告警的只读观察者 |

## 读完这一 tab 之后

- 想照着抄：[Cookbook](../cookbook/index.md) 每个 recipe 是 `examples/`
  里的一个可跑脚本。
- 想看起来什么样：[Demos](../demos/index.md) 两个带前端的可视化应用。
- 想查某个符号的完整签名：[API 参考](../api/step.md) 从 docstring 自动生成。
