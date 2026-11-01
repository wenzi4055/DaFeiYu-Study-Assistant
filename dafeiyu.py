#!/usr/bin/env python3
"""大肥鱼监工器 - 三科考试进度悬浮窗

三态规则：待完成 / 在途 / 已过关。只有「已过关」计入完成度，随时可打回。
状态持久化到同目录 dafeiyu_state.json（可直接手改）。
模块三（离散数学）冻结，不进分母。

用法: python dafeiyu.py            正常启动
      python dafeiyu.py --smoke    自检启动，0.8 秒后自动退出
      python dafeiyu.py --version  输出版本号
键位: 拖动标题栏移动 / 双击标题栏折叠 / Esc 展开
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import tkinter as tk

__version__ = "0.4.0"

# 打包成 exe 后 __file__ 指向临时解压目录，配置与进度必须落在 exe 旁边
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
STATE_FILE = APP_DIR / "dafeiyu_state.json"
TASKS_FILE = APP_DIR / "tasks.json"

# 内置示例任务池（首次运行时写出 tasks.json，之后一切以 tasks.json 为准）
# (id, 模块, 列表短名, 详情全名, 验收标准)
DEFAULT_TASKS = [
    ("ds1", "数据结构", "数组与广义表", "数组与广义表 · 重建", [
        "地址公式 3 分钟内默写（一/二/三维），说明每层偏移怎么变",
        "同一 3×4 矩阵按行优先、按列优先双算地址，零误差",
        "对称/三角/三对角压缩公式默写 + 各代 2 组数值验证",
        "广义表 GetHead/GetTail/Depth/Length 5 题全对",
        "手画 ((a,b),(c,(d))) 链式存储图，tag/原子/表结点齐全",
        "限时自测 15 题 25 分钟，得分 ≥90",
    ]),
    ("ds2", "数据结构", "树与二叉树", "树与二叉树（遍历、性质）", [
        "三种遍历手写互推，不查表不卡顿",
        "由两种遍历序列还原唯一二叉树，10 题全对",
        "完全二叉树父子下标公式默写 + 节点数性质推导",
        "树/森林/二叉树相互转换画图正确",
        "线索二叉树前中后序线索 10 分钟内画完",
        "手写非递归遍历代码并跑通输出",
    ]),
    ("ds3", "数据结构", "图（DFS/BFS）", "图（邻接表、DFS/BFS）", [
        "邻接矩阵 / 邻接表互转 5 题",
        "DFS/BFS 遍历序列手写 10 题全对",
        "Prim / Kruskal / Dijkstra 手算各 1 题全对",
        "AOV 拓扑排序 + AOE 关键路径各 1 题",
        "手写 DFS/BFS 代码跑通",
    ]),
    ("ds4", "数据结构", "排序与查找", "排序与查找（复杂度、手写核心逻辑）", [
        "冒泡/插入/希尔/快排/归并/堆排代码手写全跑通",
        "乱序数组手工推每趟结果，不查表",
        "复杂度 + 稳定性对照表默写",
        "折半查找判定树画对，ASL 计算正确",
        "哈希线性探测 / 链地址各算 1 题",
    ]),
    ("ds5", "数据结构", "数据结构真题", "冲刺：近 5 年数据结构真题", [
        "近 5 年真题数据结构部分限时完成",
        "正确率 ≥85%",
        "错题逐条归因，落成错题本",
        "重复错的知识点回炉重做并复测通过",
    ]),
    ("ne1", "软考网工", "网工破冰", "破冰：第 0 章导学 + 第 1 章 + 第 3 章体系结构", [
        "录播倍速看完，笔记落地",
        "OSI 七层与 TCP/IP 四层对照默写",
        "每层典型协议 + 设备默写",
        "课后题正确率 ≥80%",
    ]),
    ("ne2", "软考网工", "因特网计算", "核心计算：第 6 章因特网（IP/子网/路由）", [
        "任意 IP+掩码算网络地址/广播地址/可用主机数，10 题全对",
        "VLSM 划分子网 3 题正确",
        "CIDR 路由聚合 2 题正确",
        "RIP 距离向量手算一跳 + 与 OSPF 区别默写",
    ]),
    ("ne3", "软考网工", "局域网/管理/安全", "核心理论：第 4 章局域网 + 第 7 章管理 + 第 8 章安全", [
        "CSMA/CD、以太网帧格式、VLAN、SNMP 默写",
        "加密体系 / 防火墙 / IDS 概念默写",
        "选择题 20 题 ≥85%",
    ]),
    ("ne4", "软考网工", "设备配置实操", "核心实操：第 9-10 章设备配置（模拟器敲命令）", [
        "模拟器独立搭 3 个拓扑：VLAN 互通 / 静态路由 / ACL 或 NAT",
        "每条命令能说出作用，不看教程重敲一遍成功",
        "截图或配置文件留档",
    ]),
    ("ne5", "软考网工", "网工真题", "冲刺：历年真题上午卷 + 下午案例", [
        "上午卷限时完成，正确率达合格线以上",
        "近 3 年下午案例各做 1 套并对照答案",
        "错题归因落本",
    ]),
]

APP_TITLE = "大肥鱼监工器"
NOTE = ""
UNIT = "项大任务"
TASKS = []
TOTAL = 0
TASK_BY_ID = {}

# 每项预计投入小时数（学 + 练 + 测）。依据：内容量 × 视频倍速 × 练习系数。
# 改了 tasks.json 却没写 hours 时，按 id 查这张表兜底。
HOURS = {
    "ds1": 4, "ds2": 12, "ds3": 11, "ds4": 11, "ds5": 14,
    "ne1": 7, "ne2": 13, "ne3": 13, "ne4": 16, "ne5": 22,
}


def _default_config():
    return {
        "title": "大肥鱼监工器",
        "note": "离散数学冻结不计数",
        "unit": "项大任务",
        "tasks": [{"id": i, "module": m, "short": s, "full": f,
                   "criteria": list(c), "hours": HOURS.get(i, 0)}
                  for i, m, s, f, c in DEFAULT_TASKS],
    }


def load_config():
    """读同目录 tasks.json。缺失就写出内置示例；损坏就回退内置，不让程序起不来。"""
    global APP_TITLE, NOTE, UNIT, TASKS, TOTAL, TASK_BY_ID
    raw = None
    if TASKS_FILE.exists():
        try:
            raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = None
    if not isinstance(raw, dict) or not isinstance(raw.get("tasks"), list) or not raw["tasks"]:
        raw = _default_config()
        try:
            TASKS_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    APP_TITLE = raw.get("title") or "大肥鱼监工器"
    NOTE = raw.get("note") or ""
    UNIT = raw.get("unit") or "项大任务"
    tasks = []
    for n, t in enumerate(raw["tasks"], 1):
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or f"task{n}")
        short = t.get("short") or t.get("full") or tid
        try:
            hours = float(t.get("hours") if t.get("hours") is not None else HOURS.get(tid, 0))
        except (TypeError, ValueError):
            hours = float(HOURS.get(tid, 0))
        tasks.append((tid, t.get("module") or "", short, t.get("full") or short,
                      [str(c) for c in (t.get("criteria") or [])], hours))
    if not tasks:                      # 全是不合法条目时仍给一份可用的
        raw = _default_config()
        tasks = [(i, m, s, f, list(c)) for i, m, s, f, c in DEFAULT_TASKS]
    TASKS = tasks
    TOTAL = len(TASKS)
    TASK_BY_ID = {t[0]: t for t in TASKS}

BG = "#1B1D1F"
CARD = "#24272A"
SEL = "#2E3236"
LINE = "#33383D"
FG = "#E6E6E6"
DIM = "#9AA0A6"
MUTED = "#7C848C"
ACCENT = "#4FC3F7"
OK = "#7DD87D"
DOING = "#FFB74D"
FONT = "微软雅黑"

W = 420
H_MAX = 680
ALPHA = 1.0   # 想要玻璃感就改 0.92，代价是底下窗口内容会透上来


class DaFeiYu:
    def __init__(self, root):
        self.root = root
        self.state = self._load()
        self.collapsed = False
        self.selected = self._first_open()

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", ALPHA)
        root.configure(bg=BG)
        self.h = self._target_h()
        self._place(W, self.h)

        self._build_titlebar()
        self.body = tk.Frame(root, bg=BG)
        self.body.pack(fill="both", expand=True)
        self._build_progress()
        self._build_detail()   # 先占住底部，保证详情永不被列表挤掉
        self._build_list()

        root.bind("<Escape>", lambda e: self._expand())

    # ---------- 持久化 ----------
    def _load(self):
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("tasks", {})
        except Exception:
            data = {}
        return {tid: data.get(tid, {"state": "todo", "ts": ""}) for tid, *_ in TASKS}

    def _save(self):
        STATE_FILE.write_text(json.dumps(
            {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "tasks": self.state},
            ensure_ascii=False, indent=2), encoding="utf-8")

    def _first_open(self):
        for tid, *_ in TASKS:
            if self.state[tid]["state"] != "done":
                return tid
        return TASKS[0][0]

    # ---------- 布局 ----------
    def _target_h(self):
        return min(H_MAX, self.root.winfo_screenheight() - 160)

    def _place(self, w, h):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw - w - 36}+{max(30, sh // 8)}")

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg="#141618", height=32)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=APP_TITLE, bg="#141618", fg=FG,
                 font=(FONT, 10, "bold")).pack(side="left", padx=12)
        tk.Button(bar, text="✕", command=self.root.destroy, bg="#141618", fg=MUTED,
                  bd=0, activebackground="#8B3A3A", activeforeground="white",
                  font=(FONT, 11), cursor="hand2").pack(side="right", padx=(0, 6))
        self.fold_btn = tk.Button(bar, text="—", command=self._toggle, bg="#141618", fg=MUTED,
                                  bd=0, activebackground=LINE, activeforeground=FG,
                                  font=(FONT, 11), cursor="hand2")
        self.fold_btn.pack(side="right", padx=2)
        tk.Label(bar, text=f"v{__version__}", bg="#141618", fg="#4A5056",
                 font=(FONT, 7)).pack(side="right", padx=(0, 4))
        bar.bind("<ButtonPress-1>", self._drag_start)
        bar.bind("<B1-Motion>", self._drag)
        bar.bind("<Double-Button-1>", lambda e: self._toggle())

    def _drag_start(self, e):
        self._ox, self._oy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def _drag(self, e):
        self.root.geometry(f"+{e.x_root - self._ox}+{e.y_root - self._oy}")

    def _build_progress(self):
        wrap = tk.Frame(self.body, bg=BG)
        wrap.pack(fill="x", padx=14, pady=(12, 4))
        self.pct = tk.Label(wrap, text="0%", bg=BG, fg=ACCENT, font=(FONT, 24, "bold"))
        self.pct.pack(side="left")
        right = tk.Frame(wrap, bg=BG)
        right.pack(side="left", padx=(12, 0))
        self.left_label = tk.Label(right, text="", bg=BG, fg=FG, font=(FONT, 10, "bold"))
        self.left_label.pack(anchor="w")
        self.sub_label = tk.Label(right, text="", bg=BG, fg=MUTED, font=(FONT, 8))
        self.sub_label.pack(anchor="w")
        self.bar = tk.Canvas(self.body, height=5, bg=CARD, highlightthickness=0)
        self.bar.pack(fill="x", padx=14, pady=(8, 8))
        self.bar_fill = self.bar.create_rectangle(0, 0, 0, 5, fill=ACCENT, width=0)
        self.bar.bind("<Configure>", lambda e: self._draw_bar())

    def _build_detail(self):
        wrap = tk.Frame(self.body, bg=CARD)
        wrap.pack(side="bottom", fill="x", padx=12, pady=(6, 10))
        self.detail_title = tk.Label(wrap, text="", bg=CARD, fg=ACCENT,
                                     font=(FONT, 9, "bold"), anchor="w", justify="left",
                                     wraplength=W - 44)
        self.detail_title.pack(fill="x", padx=10, pady=(8, 4))
        self.detail_text = tk.Text(wrap, height=6, bg=CARD, fg=DIM, bd=0,
                                   font=(FONT, 8), wrap="word", cursor="arrow",
                                   highlightthickness=0, padx=0, pady=0,
                                   selectbackground=CARD, spacing1=1, spacing3=3)
        self.detail_text.pack(fill="x", padx=10)
        self.detail_text.bind("<MouseWheel>", self._detail_wheel)

        btns = tk.Frame(wrap, bg=CARD)
        btns.pack(fill="x", padx=8, pady=6)
        for text, color, st in (("✔ 过关", OK, "done"),
                                ("◐ 在途", DOING, "doing"),
                                ("↺ 打回", "#E57373", "todo")):
            tk.Button(btns, text=text, command=lambda s=st: self._set(s),
                      bg=CARD, fg=color, bd=1, relief="flat", highlightbackground=LINE,
                      activebackground=color, activeforeground="#111",
                      font=(FONT, 9, "bold"), cursor="hand2", width=8).pack(side="left", padx=3)

    def _build_list(self):
        shell = tk.Frame(self.body, bg=BG)
        shell.pack(fill="both", expand=True, padx=10)
        self.listbox = tk.Canvas(shell, bg=BG, highlightthickness=0)
        self.listbox.pack(fill="both", expand=True)
        inner = tk.Frame(self.listbox, bg=BG)
        self._inner = self.listbox.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: self.listbox.configure(scrollregion=self.listbox.bbox("all")))
        self.listbox.bind("<Configure>",
                          lambda e: self.listbox.itemconfigure(self._inner, width=e.width))

        self.rows = {}
        for tid, mod, short, _, _, _h in TASKS:
            row = tk.Frame(inner, bg=CARD, cursor="hand2")
            row.pack(fill="x", pady=1)
            dot = tk.Label(row, text="○", bg=CARD, fg=MUTED, font=(FONT, 8))
            dot.pack(side="left", padx=(8, 6), pady=2)
            name = tk.Label(row, text=short, bg=CARD, fg=FG, font=(FONT, 9), anchor="w")
            name.pack(side="left", fill="x", expand=True)
            tag = tk.Label(row, text=mod, bg=CARD, fg=MUTED, font=(FONT, 7))
            tag.pack(side="right", padx=8)
            for w in (row, dot, name, tag):
                w.bind("<Button-1>", lambda e, t=tid: self._select(t))
                w.bind("<MouseWheel>", self._wheel)
                w.configure(cursor="hand2")
            self.rows[tid] = (row, dot, name, tag)

    # ---------- 滚轮 ----------
    def _wheel(self, e):
        first, last = (float(v) for v in self.listbox.yview())
        if first <= 0.0 and last >= 1.0:      # 内容没超出可视区，滚动无意义
            return
        self.listbox.yview_scroll(-1 * (e.delta // 120), "units")
        return "break"

    def _detail_wheel(self, e):
        first, last = (float(v) for v in self.detail_text.yview())
        if first <= 0.0 and last >= 1.0:
            return
        self.detail_text.yview_scroll(-1 * (e.delta // 120), "units")
        return "break"

    # ---------- 交互 ----------
    def _toggle(self):
        if self.collapsed:
            self._expand()
        else:
            self.collapsed = True
            self.body.pack_forget()
            self.root.geometry(f"{W}x32")
            self.fold_btn.config(text="▢")

    def _expand(self):
        if not self.collapsed:
            return
        self.collapsed = False
        self.body.pack(fill="both", expand=True)
        self.h = self._target_h()
        self.root.geometry(f"{W}x{self.h}")
        self.fold_btn.config(text="—")

    def _select(self, tid):
        self.selected = tid
        self._refresh()

    def _set(self, st):
        tid = self.selected
        self.state[tid] = {"state": st, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
        self._save()
        if st == "done":
            self.selected = self._first_open()
        self._refresh()

    # ---------- 渲染 ----------
    def _draw_bar(self):
        done = sum(1 for v in self.state.values() if v["state"] == "done")
        w = max(self.bar.winfo_width(), 1)
        self.bar.coords(self.bar_fill, 0, 0, w * done / max(TOTAL, 1), 5)

    def _refresh(self):
        done = sum(1 for v in self.state.values() if v["state"] == "done")
        remain_h = sum(h for tid, _, _, _, _, h in TASKS
                       if self.state[tid]["state"] != "done")
        self.pct.config(text=f"{done * 100 // max(TOTAL, 1)}%")
        self.left_label.config(text=f"还剩 {TOTAL - done} {UNIT} · {remain_h:g}h")
        self.sub_label.config(text=f"已过关 {done} / {TOTAL}" + (f"  ·  {NOTE}" if NOTE else ""))
        self._draw_bar()

        for tid, _, short, _, _, _h in TASKS:
            row, dot, name, tag = self.rows[tid]
            st = self.state[tid]["state"]
            color = {"done": OK, "doing": DOING, "todo": MUTED}[st]
            mark = {"done": "✔", "doing": "◐", "todo": "○"}[st]
            bg = SEL if tid == self.selected else CARD
            for w in (row, dot, name, tag):
                w.configure(bg=bg)
            dot.config(text=mark, fg=color)
            name.config(fg=DIM if st == "done" else FG)

        _, _, _, full, crit, hours = TASK_BY_ID[self.selected]
        self.detail_title.config(text=f"{full}    〔预计 {hours:g}h〕")
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("end", "\n".join(f"{i}. {c}" for i, c in enumerate(crit, 1))
                                or "（该项没写验收标准，补一条可当场判真假的句子）")
        self.detail_text.config(state="disabled")
        self.detail_text.yview_moveto(0)


def _enable_dpi_awareness():
    """Windows 高 DPI 下不声明感知，Tk 窗口会被系统位图拉伸，字是糊的。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except Exception:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # system DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    if "--version" in sys.argv:
        print(f"DaFeiYu {__version__}")
        return
    load_config()
    _enable_dpi_awareness()
    root = tk.Tk()
    app = DaFeiYu(root)
    app._refresh()
    if not STATE_FILE.exists():
        app._save()
    if "--smoke" in sys.argv:
        root.after(800, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
