"""通用性验证：任意 tasks.json 都能驱动同一个窗口。"""
import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tkinter as tk

import dafeiyu

STATE = ROOT / "dafeiyu_state.json"
TASKS = ROOT / "tasks.json"
for f in (STATE, TASKS):
    f.unlink(missing_ok=True)

# 1) 缺失配置 -> 自动写出内置示例
dafeiyu.load_config()
print("自动生成 tasks.json:", TASKS.exists(), "| 任务数:", dafeiyu.TOTAL,
      "| 标题:", dafeiyu.APP_TITLE)

# 2) 换成完全无关的监督对象：3 项，模块名/标题都变
TASKS.write_text(json.dumps({
    "title": "健身监督器",
    "note": "增肌期第 3 周",
    "unit": "项训练",
    "tasks": [
        {"id": "g1", "module": "力量", "short": "深蹲 5x5", "full": "深蹲 5×5 @ 60kg",
         "criteria": ["最后一组可完成 5 次", "组间休息 ≤3 分钟"]},
        {"id": "g2", "module": "力量", "short": "卧推 5x5", "full": "卧推 5×5 @ 40kg",
         "criteria": ["肩胛收紧不塌肩", "触胸停顿 1 秒"]},
        {"id": "g3", "module": "有氧", "short": "慢跑 5km", "full": "慢跑 5km / 30 分钟内",
         "criteria": ["配速 ≤6:00", "跑完不复盘不算"]},
    ],
}, ensure_ascii=False), encoding="utf-8")

dafeiyu.load_config()
print("自定义 tasks.json -> 任务数:", dafeiyu.TOTAL, "| 标题:", dafeiyu.APP_TITLE)
assert dafeiyu.TOTAL == 3 and dafeiyu.APP_TITLE == "健身监督器"

root = tk.Tk()
app = dafeiyu.DaFeiYu(root)
app._refresh()
app._select("g2")
print("进度:", app.pct.cget("text"), "|", app.left_label.cget("text"), "|", app.today_label.cget("text"))
print("列表行数:", len(app.rows), "| 详情标题:", app.detail_title.cget("text"))
print("详情内容:", app.detail_text.get("1.0", "end").strip().replace("\n", " / "))

app._set("done")
print("过关 g2 ->", app.pct.cget("text"), "|", app.left_label.cget("text"),
      "| 自动选中:", app.selected)
assert app.pct.cget("text") == "33%"
assert "项训练" in app.left_label.cget("text")
root.destroy()

# 3) 损坏的 tasks.json 不致命
TASKS.write_text("{ 这不是 json", encoding="utf-8")
dafeiyu.load_config()
print("损坏配置 -> 回退任务数:", dafeiyu.TOTAL, "| 标题:", dafeiyu.APP_TITLE)
# 不硬编码项数：回退后应当等于源码默认任务数，项数变化不该让测试失败
assert dafeiyu.TOTAL == len(dafeiyu.DEFAULT_TASKS), \
    f"回退后项数 {dafeiyu.TOTAL} != 源码默认 {len(dafeiyu.DEFAULT_TASKS)}"

for f in (STATE, TASKS):
    f.unlink(missing_ok=True)
print("全部通过")
