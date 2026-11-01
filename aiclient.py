#!/usr/bin/env python3
"""AI 批改客户端 - OpenAI 兼容接口，零第三方依赖。

只做一件事：把你的汇报和该项的验收标准一起发给模型，让它按固定格式判
「通过 / 勉强 / 打回」。不改变本地记账规则 —— 进度仍然只由你点「过关」决定。

配置读取顺序：同目录 config.json -> 内置默认（无 key 时功能不可用）。
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

__version__ = "0.5.0"

# 预设服务商：base_url 与默认模型都填好，用户只填 key 即可
PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek（便宜，推荐）",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "apply": "https://platform.deepseek.com/api_keys",
        "cost": "约 ¥0.001 / 次批改",
    },
    "kimi": {
        "name": "Kimi / Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "apply": "https://platform.moonshot.cn/console/api-keys",
        "cost": "约 ¥0.01 / 次批改",
    },
    "qwen": {
        "name": "通义千问（有免费额度）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "apply": "https://bailian.console.aliyun.com/?apiKey=1",
        "cost": "新用户有免费 token 额度",
    },
    "zhipu": {
        "name": "智谱 GLM（有免费额度）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "apply": "https://open.bigmodel.cn/usercenter/apikeys",
        "cost": "glm-4-flash 免费",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "apply": "https://platform.openai.com/api-keys",
        "cost": "约 ¥0.01 / 次批改，需外币卡",
    },
    "custom": {
        "name": "自填（任何 OpenAI 兼容服务）",
        "base_url": "",
        "model": "",
        "apply": "",
        "cost": "",
    },
}

DEFAULT_CONFIG = {
    "provider": "deepseek",
    "base_url": PROVIDERS["deepseek"]["base_url"],
    "model": PROVIDERS["deepseek"]["model"],
    "api_key": "",
    "timeout": 90,
    "proxy": "",                  # 例如 http://127.0.0.1:12000，留空直连
    "system_prompt": "",          # 留空用内置监工人格
}

DEFAULT_SYSTEM = """你是「大肥鱼」，一个只认标准不认感觉的监工。

你的任务：根据【验收标准】判断【我的汇报】是否达标。只输出四行，不要寒暄：

【判定】🟢通过 / 🟡勉强 / 🔴打回
【漏洞】逐条列出没做到的地方；全部做到就写「无」
【依据】一句话说明你为什么这么判
【建议】通过 / 补做哪一项后再来

判定规则：
- 汇报里没有可核验的过程或数字，一律 🔴打回，理由写「无过程无数据」
- 只给结论不给推导 → 🔴
- 承认部分不会但明确说清漏洞在哪 → 至少 🟡，不许因为「态度好」给 🟢
- 禁止夸奖、禁止"你可以的"、"继续加油"、"相信自己"这类话
"""


class AIError(Exception):
    """API 调用失败，消息直接给用户看。"""


def config_path(app_dir):
    return Path(app_dir) / "config.json"


def load_config(app_dir):
    """读 app_dir/config.json，缺字段用默认补齐。文件不存在就写一份出来。"""
    path = config_path(app_dir)
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k in DEFAULT_CONFIG:
                    if k in raw:
                        cfg[k] = raw[k]
        except Exception:
            pass            # 配置坏了就用默认，不让程序起不来
    else:
        try:
            path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return cfg


def save_config(app_dir, cfg):
    path = config_path(app_dir)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def is_ready(cfg):
    return bool((cfg.get("api_key") or "").strip() and (cfg.get("base_url") or "").strip()
                and (cfg.get("model") or "").strip())


VISION_HINTS = ("vl", "vision", "4o", "glm-4v", "gemini", "omni", "gpt-4.1", "gpt-5")


def supports_vision(model):
    """粗略判断模型能不能读图。判错也只是白试一次，不影响记账。"""
    m = (model or "").lower()
    return any(k in m for k in VISION_HINTS)


def build_messages(cfg, task_full, criteria, report, attachments=None, sessions=None):
    """attachments: [{"b64": "...", "mime": "image/png"}]，sessions: 最近学习记录文本列表。"""
    system = (cfg.get("system_prompt") or "").strip() or DEFAULT_SYSTEM
    crit = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1)) or "（该项未设验收标准）"
    parts = [f"【任务】{task_full}", "", "【验收标准】", crit]
    if sessions:
        parts += ["", "【我的学习记录（程序记录，可能造假，仅供参考）】"]
        parts += [f"- {s}" for s in sessions]
    parts += ["", "【我的汇报】", report.strip() or "（没写文字，看附件）"]
    if attachments:
        parts += ["", f"【附件】共 {len(attachments)} 张图片，手写推导或截图。"
                      "请按验收标准逐条核对图里的推导过程，指出具体哪一步错。"]
    parts += ["", "按四行格式输出判定。"]
    text = "\n".join(parts)

    if attachments:
        content = [{"type": "text", "text": text}]
        for a in attachments:
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:{a.get('mime', 'image/png')};base64,{a['b64']}"}})
        user_content = content
    else:
        user_content = text
    return [{"role": "system", "content": system},
            {"role": "user", "content": user_content}]


def _opener(cfg):
    proxy = (cfg.get("proxy") or "").strip()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def review(cfg, task_full, criteria, report, attachments=None, sessions=None):
    """调用模型批改。成功返回文本，失败抛 AIError（消息可直接展示）。"""
    if not is_ready(cfg):
        raise AIError("还没配置 API Key。点「API 设置」填一个，或看 API_SETUP.md 的引导。")
    if attachments and not supports_vision(cfg.get("model")):
        raise AIError(f"当前模型 {cfg.get('model')} 看不了图片。\n"
                      "换成支持视觉的模型：qwen-vl-max / glm-4v-flash / gpt-4o-mini。\n"
                      "或者把推导打字贴进来。")
    base = (cfg.get("base_url") or "").rstrip("/")
    url = base + "/chat/completions"
    payload = {
        "model": cfg.get("model"),
        "messages": build_messages(cfg, task_full, criteria, report, attachments, sessions),
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {cfg.get('api_key').strip()}",
        "User-Agent": f"DaFeiYu/{__version__}",
    })
    try:
        with _opener(cfg).open(req, timeout=float(cfg.get("timeout") or 90)) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        hint = {401: "Key 无效或已过期", 402: "账户余额不足", 403: "该 Key 无此模型权限",
                404: "base_url 或 model 名写错", 429: "触发限流，稍后再试"}.get(e.code, "接口报错")
        raise AIError(f"HTTP {e.code} · {hint}\n{detail}") from e
    except urllib.error.URLError as e:
        raise AIError(f"网络不通：{e.reason}\n"
                      f"国内访问 OpenAI 需要在 config.json 的 proxy 字段填本地代理地址。") from e
    except TimeoutError:
        raise AIError("请求超时。模型在忙或网络卡，重试一次；仍不行就调小 config.json 里的 timeout。")

    try:
        obj = json.loads(body)
        return obj["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise AIError(f"返回格式看不懂：{body[:300]}") from e


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT_EXTS = {".txt", ".md", ".py", ".c", ".cpp", ".h", ".java", ".cs", ".json", ".log", ".csv"}
MAX_IMAGE_BYTES = 6 * 1024 * 1024      # base64 膨胀约 1.33 倍，别撑爆请求


def read_attachment(path):
    """读一个附件。图片返回 ("image", {"b64","mime"})，文本返回 ("text", 内容)。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in IMAGE_EXTS:
        size = p.stat().st_size
        if size > MAX_IMAGE_BYTES:
            raise AIError(f"{p.name} 有点大（{size/1024/1024:.1f} MB），先压到 6 MB 以内。")
        import base64
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
        return "image", {"b64": base64.b64encode(p.read_bytes()).decode("ascii"),
                         "mime": mime, "name": p.name}
    if ext in TEXT_EXTS or ext == "":
        try:
            return "text", p.read_text(encoding="utf-8", errors="replace")[:20000]
        except Exception as e:
            raise AIError(f"读不了 {p.name}：{e}") from e
    raise AIError(f"不支持的文件类型 {ext}。目前能收图片和文本类文件。")


def test_connection(cfg):
    """发一次最小请求验证配置。返回一句话结果，失败抛 AIError。"""
    if not is_ready(cfg):
        raise AIError("Key / base_url / model 有空项，先填全。")
    base = (cfg.get("base_url") or "").rstrip("/")
    payload = {"model": cfg.get("model"),
               "messages": [{"role": "user", "content": "回复两个字：通了"}],
               "max_tokens": 16}
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {cfg.get('api_key').strip()}",
                                          "User-Agent": f"DaFeiYu/{__version__}"})
    try:
        with _opener(cfg).open(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode("utf-8", "replace"))
        return f"连接正常，模型返回：{obj['choices'][0]['message']['content'].strip()[:20]}"
    except urllib.error.HTTPError as e:
        raise AIError(f"HTTP {e.code} · Key 或模型名不对") from e
    except Exception as e:
        raise AIError(f"连不上：{e}") from e
