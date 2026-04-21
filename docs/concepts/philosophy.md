# 哲学与定位

## 一句话

> **LLM 的输出喂给下一段代码，不是喂给人眼。**

首页已经亮过这句话。这里讲：为什么它值得写进框架里。

## 代码消费 vs 人类消费

多数 agent 框架默认 LLM 在跟人对话。ChatGPT 是这样，Claude Desktop 是这样，
LangChain 的 conversational agent 也是这样。LLM 说一段话，应用层直接显示——
自然语言本身就是产品。

pyxis 换一个前提：**LLM 的每一次输出都要被下一段 Python 代码消费**。

这不是小细节。定下这个前提，一连串设计自动被约束：

- **输出必须结构化**。自然语言不是结构，所以强制 Pydantic。
- **输出必须可回放**。`TraceRecord` 里是 Pydantic 实例，不是 markdown。
  `assert trace.records[-1].output == Expected(...)` 一行就够。
- **prompt 必须可追踪**。函数 docstring 就是 prompt，git 自动管它的版本；
  不存在一个神秘的 template engine 中转层。
- **推理步骤必须显式**。Schema 字段顺序就是思维链——改顺序=改推理。

对话型框架也能做到这些，但没动力去做——丝滑对话才是它们的主产品。pyxis
反过来：**结构性**是主产品，对话丝滑度从来不是我们的战场。

## 不做 LangChain-lite

这点最容易走偏。

"像 LangChain 但更小"——这种定位听起来吸引人，哲学上却是错的。LangChain 的
价值主张是"我把一切封装好，你组合就行"，**越完善越赢**。顺着这个方向做小，
就是做一个残废版 LangChain。

pyxis 的价值主张正好相反：**尽量少做**。

不做的东西：

- 图式 DSL、YAML pipeline、节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute 都不做）
- function-calling 协议适配层——Pydantic 判别式联合就够了
- 内置 memory / vector store 抽象
- prompt 模板语言——docstring 就是模板
- 全局 registry——显式 import 永远比注册表好找

**"这些不做"比"有什么功能"更能说明 pyxis 是什么。**
