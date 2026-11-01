# API 接入引导

AI 批改是**可选功能**。不配 API Key，程序照常记账、打卡、显示工时，一点不受影响 —— 只是没有「AI 批改」那一栏。

想用，按下面走，全程约 3 分钟。

---

## 一、选一家服务商

国内能用、按量计费的都在下面。**先用 DeepSeek**，便宜、直连不用代理、注册流程最短。

| 服务商 | 申请地址 | 默认模型 | 一次批改大概 |
|---|---|---|---|
| **DeepSeek**（推荐，纯文字） | https://platform.deepseek.com/api_keys | `deepseek-chat` | ≈ ¥0.001 |
| 通义千问（**能读图**） | https://bailian.console.aliyun.com/?apiKey=1 | `qwen-vl-max` | 新用户有免费额度 |
| 智谱 GLM（**能读图**） | https://open.bigmodel.cn/usercenter/apikeys | `glm-4v-flash` | 免费 |
| Kimi / Moonshot | https://platform.moonshot.cn/console/api-keys | `moonshot-v1-8k` | ≈ ¥0.01 |
| OpenAI（**能读图**） | https://platform.openai.com/api-keys | `gpt-4o-mini` | ≈ ¥0.01，需外币卡 + 代理 |

**要传手写推导照片，必须选能读图的模型。** `deepseek-chat` 只认文字 —— 想拍照交作业，就把 `model` 换成 `qwen-vl-max` 或 `glm-4v-flash`（后者免费）。程序会自己判断，不支持时直接提示你换哪个。

当前识别规则：模型名里含 `vl` / `vision` / `4o` / `glm-4v` / `gemini` / `omni` 视为支持视觉。

**一次批改 ≈ 1500 token**（验收标准 + 你的汇报进，判定结果出）。一天批 3 次，一个月不到 3 毛钱。这个功能不会让你破费，但**它也不是必须的**。

## 二、拿 Key 的三步（以 DeepSeek 为例）

1. 打开 https://platform.deepseek.com ，手机号注册登录
2. 左侧菜单 **API keys** → **创建 API key** → 起个名字（随便写，比如 `dafeiyu`）
3. 复制那串 `sk-` 开头的字符。**只显示一次**，关掉就再也看不到，只能删了重建

新账号一般有赠送额度，够你测很久。

## 三、填进程序

**方式一：界面里填**

点主窗口标题栏的 **API** 按钮 → 服务商下拉选 `deepseek`（`base_url` 和 `model` 会自动填好）→ 把 Key 粘进 `api_key` → 点 **测试连接** → 看到「连接正常」再点 **保存**。

**方式二：直接改文件**

程序旁边有 `config.json`（第一次启动自动生成）。也可以照 [`config.example.json`](../config.example.json) 复制一份改名：

```json
{
  "provider": "deepseek",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "api_key": "sk-你的Key",
  "timeout": 90,
  "proxy": "",
  "system_prompt": ""
}
```

| 字段 | 说明 |
|---|---|
| `provider` | 只是给界面下拉框记个名字，不影响调用 |
| `base_url` | 到 `/v1` 为止，**不要**自己拼 `/chat/completions` |
| `model` | 必须是你账号有权限的模型名，写错会报 404 |
| `api_key` | 那串 `sk-` 开头的 |
| `timeout` | 秒。网络慢就调大 |
| `proxy` | 国内访问 OpenAI 才需要，例如 `http://127.0.0.1:12000`；DeepSeek 等国内服务留空 |
| `system_prompt` | **留空用内置监工人格**；想换语气就在这里写自己的 |

**任何 OpenAI 兼容接口都能用**：把 `base_url` 和 `model` 改成你的服务即可，界面里选「自填」。

## 四、批改是怎么判的

点 `AI 批改` → 贴你的推导/汇报 → 提交。程序把三样东西发出去：**当前任务的完整名称、这项的全部验收标准、你的汇报**。

模型固定回四行：

```
【判定】🟢通过 / 🟡勉强 / 🔴打回
【漏洞】逐条列出没做到的地方；全部做到写「无」
【依据】一句话说明为什么这么判
【建议】通过 / 补做哪一项后再来
```

判定规则写死在提示词里，其中三条是关键：

- 汇报里没有可核验的过程或数字 → 一律 🔴，理由「无过程无数据」
- 只给结论不给推导 → 🔴
- 承认不会但说清漏洞在哪 → 至少 🟡，**不许因为态度好给 🟢**

**AI 判 🟢 也不会自动帮你过关。** 进度始终只由你点「✔ 过关」决定 —— 这是有意的设计：批改是第二双眼睛，不是替你负责的人。

## 五、报错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `HTTP 401` | Key 无效、复制不全、或已删除 | 重新生成 Key |
| `HTTP 402` | 账户余额不足 | 充值，或换免费额度模型（`glm-4-flash`） |
| `HTTP 403` | 这个 Key 没权限用该模型 | 换 `model` |
| `HTTP 404` | `base_url` 或 `model` 写错 | 照上表核对，注意结尾是 `/v1` |
| `HTTP 429` | 触发限流 | 等一分钟再试 |
| `网络不通` | 需要代理，或防火墙拦截 | 国内服务通常直连；OpenAI 需在 `proxy` 填本地代理 |
| `请求超时` | 模型在忙 | 重试；仍不行调小 `timeout` |

## 六、隐私，说清楚

- **Key 只存在本机** `config.json`，程序不上传、不联网校验、不做任何遥测，除了你点「提交批改」那一刻
- **只有你主动提交的汇报内容**会发给你选的那家服务商，被发出去的还有该项的任务名与验收标准
- **任务池、进度账本、排课表永远不出本机**
- `config.json` 已在 `.gitignore` 里，不会被误提交到 Git
- 如果你用的是公司网络或他人电脑，注意 Key 与汇报内容都可能被网络管理者看到

**不要把 Key 发到聊天、issue、截图里。** 报问题时贴错误文案就够了，Key 一个字都不需要。
