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
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog

import aiclient
import clipimg

__version__ = "0.9.1"

# 打包成 exe 后 __file__ 指向临时解压目录，配置与进度必须落在 exe 旁边
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
STATE_FILE = APP_DIR / "dafeiyu_state.json"
TASKS_FILE = APP_DIR / "tasks.json"

# 内置示例任务池（首次运行时写出 tasks.json，之后一切以 tasks.json 为准）
# (id, 模块, 列表短名, 详情全名, 验收标准)
DEFAULT_TASKS = [
    ("ds0", "数据结构", "线性表/栈/队列", "第 1-3 章：绪论 + 线性表 + 栈和队列", [
        "单链表：头插、尾插、按值删除、就地逆置，代码手写全部跑通",
        "双链表与循环链表：能画图说清插入删除时到底改几个指针",
        "栈：顺序栈 / 链栈 push-pop 跑通，括号匹配 + 表达式求值各 1 题",
        "队列：循环队列判空/判满公式默写，链队列入队出队跑通",
        "复杂度：各操作 O(1) 还是 O(n)，能当场说明理由",
        "第 2 章课后练习全做，正确率 ≥80%",
    ]),
    ("ds1", "数据结构", "数组与广义表", "数组与广义表 · 初学打通", [
        "能画出 8 个元素的连续内存格子图，每个格子标出地址",
        "能说清「数组为什么不用遍历就能算出地址」——连续、等长、可乘",
        "能自己从格子图推出 base + i×L，而不是背下来",
        "二维：能说清「第 i 行之前有 i-1 整行」，据此推出行优先公式",
        "行优先 / 列优先同一个矩阵双算，两个结果互相对得上",
        "对称矩阵压缩：能代 2 组具体数字验证公式成立",
        "广义表：说清「头是元素、尾一定是表」，head/tail 各做对 3 题",
        "画出 ((a,b),(c,(d))) 链式存储图，tag/原子/表结点齐全",
        "最后才是限时测：15 题 25 分钟 ≥90（收尾，不是起点）",
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
    ("ne1", "软考网工", "网工破冰", "破冰：第 0 章导学 + 第 1 章硬件 + 第 2 章数据通信 + 第 3 章体系结构", [
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
    ("ne3", "软考网工", "局域网/管理/安全", "核心理论：第 4 章局域网 + 第 5 章广域网 + 第 7 章管理 + 第 8 章安全 + 第 11/12 章", [
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
    ("dm1", "离散数学", "离散数学（待细化）", "离散数学 · 全科（课程表到手后拆成 4-5 项）", [
        "⚠ 临时大项：还没有课程表，工时 32h 是估算，给了课程表就拆开重排",
        "命题逻辑：真值表、等价演算、主析取/主合取范式，各 5 题全对",
        "谓词逻辑：量词否定、推理规则，10 题全对",
        "集合论：集合运算、幂集、笛卡尔积，5 题全对",
        "关系：自反/对称/传递判定、等价关系与划分、偏序与哈斯图，10 题全对",
        "图论：通路、连通性、欧拉图、哈密顿图判定，10 题全对",
        "树：生成树、最小生成树、根树与二叉树表示，5 题全对",
        "代数系统：群、环、域、格的基本判定，8 题全对",
        "限时测：历年真题 1 套 ≥80",
    ]),
]

APP_TITLE = "大肥鱼监工器"
NOTE = ""
UNIT = "项大任务"
TASKS = []
TOTAL = 0
TASK_BY_ID = {}
PLAN_START = ""
PLAN_DEADLINE = ""
MINUTES_PER_DAY = 60
LEAVE_DAYS = []

# 每项预计投入小时数（学 + 练 + 测）。依据：内容量 × 视频倍速 × 练习系数。
# 改了 tasks.json 却没写 hours 时，按 id 查这张表兜底。
HOURS = {
    # 数据结构：38 讲 / 571 分钟，第一章 50.8 分钟为实测，其余按内容密度分配
    "ds0": 8.5, "ds1": 5.8, "ds2": 8.5, "ds3": 7.8, "ds4": 9.6, "ds5": 14,
    # 软考网工已按希赛录播实测校正：2659 分钟 / 1.5 倍速 / 含消化
    "ne1": 7.6, "ne2": 14.5, "ne3": 19.9, "ne4": 24.4, "ne5": 22,
    # 离散数学已解冻；还没有课程表，32h 是估算
    "dm1": 32,
}


def _default_config():
    return {
        "title": "大肥鱼监工器",
        "note": "离散数学已解冻，计入总分母",
        "unit": "项大任务",
        "plan": {"start": datetime.now().strftime("%Y-%m-%d"),
                 "deadline": "", "minutes_per_day": 60, "leave_days": []},
        "tasks": [{"id": i, "module": m, "short": s, "full": f,
                   "criteria": list(c), "hours": HOURS.get(i, 0)}
                  for i, m, s, f, c in DEFAULT_TASKS],
    }


def load_config():
    """读同目录 tasks.json。缺失就写出内置示例；损坏就回退内置，不让程序起不来。"""
    global APP_TITLE, NOTE, UNIT, TASKS, TOTAL, TASK_BY_ID
    global PLAN_START, PLAN_DEADLINE, MINUTES_PER_DAY, LEAVE_DAYS
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
    plan = raw.get("plan") if isinstance(raw.get("plan"), dict) else {}
    PLAN_START = plan.get("start") or datetime.now().strftime("%Y-%m-%d")
    PLAN_DEADLINE = plan.get("deadline") or ""
    LEAVE_DAYS = [str(d) for d in (plan.get("leave_days") or []) if d]
    try:
        MINUTES_PER_DAY = max(10, int(plan.get("minutes_per_day") or 60))
    except (TypeError, ValueError):
        MINUTES_PER_DAY = 60
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
H_MAX = 720
ALPHA = 1.0   # 想要玻璃感就改 0.92，代价是底下窗口内容会透上来


class DaFeiYu:
    def __init__(self, root):
        self.root = root
        self.sessions = []
        self.timer_start = None
        self.timer_task = None
        self.timer_job = None
        self.state = self._load()
        self.cfg = aiclient.load_config(APP_DIR)
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

    def _after_show(self):
        self._enable_taskbar()

    # ---------- 持久化 ----------
    def _load(self):
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        data = raw.get("tasks", {}) or {}
        self.sessions = [s for s in (raw.get("sessions") or []) if isinstance(s, dict)]
        return {tid: data.get(tid, {"state": "todo", "ts": ""}) for tid, *_ in TASKS}

    def _save(self):
        STATE_FILE.write_text(json.dumps(
            {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "tasks": self.state, "sessions": self.sessions},
            ensure_ascii=False, indent=2), encoding="utf-8")

    def _spent_minutes(self, tid):
        return sum(int(s.get("minutes") or 0) for s in self.sessions if s.get("task") == tid)

    def _recent_sessions(self, tid, n=3):
        rows = [s for s in self.sessions if s.get("task") == tid][-n:]
        return [f"{(s.get('end') or '')[:16]} 学了 {s.get('minutes')} 分钟：{s.get('note') or ''}"[:120]
                for s in rows]

    # ---------- 日历排期 ----------
    def _plan(self):
        """按日历切分：总工时 ÷ 每天配额 = 总天数，今天该做哪一块。

        返回 (day_no, total_days, task, quota_end, spent_all)：
        day_no 是今天第几天（1 起），task 是今天该做的任务元组。
        """
        try:
            start = datetime.strptime(PLAN_START, "%Y-%m-%d").date()
        except Exception:
            start = datetime.now().date()
        mpd = max(10, int(MINUTES_PER_DAY or 60))
        total_min = sum(h * 60 for *_, h in TASKS if h)
        if total_min <= 0:
            return 1, 1, (TASKS[0] if TASKS else None), mpd, 0
        total_days = max(1, -(-int(total_min) // mpd))       # 向上取整
        day_no = (datetime.now().date() - start).days + 1
        if day_no < 1:
            day_no = 1
        quota_min = day_no * mpd
        spent = sum(int(s.get("minutes") or 0) for s in self.sessions)

        # 定位今天配额落在哪一项
        acc = 0
        pick = TASKS[0] if TASKS else None
        for t in TASKS:
            h = t[5]
            if not h:
                continue
            tmin = h * 60
            if acc + tmin > quota_min - mpd:
                pick = t
                break
            acc += tmin
        return day_no, total_days, pick, quota_min, spent

    def _gap(self):
        """剩余工时 vs 目标完成日之间的差距：每天还差多少分钟。"""
        today = datetime.now().date()
        remain_min = sum(t[5] * 60 for t in TASKS if t[5]
                         and self.state.get(t[0], {}).get("state") != "done")
        if not PLAN_DEADLINE:
            return {"no_deadline": True, "remain_min": remain_min}
        try:
            deadline = datetime.strptime(PLAN_DEADLINE, "%Y-%m-%d").date()
        except Exception:
            return {"no_deadline": True, "remain_min": remain_min}
        total_days = (deadline - today).days + 1
        leave_left = 0
        for d in LEAVE_DAYS:
            try:
                if today <= datetime.strptime(d, "%Y-%m-%d").date() <= deadline:
                    leave_left += 1
            except Exception:
                pass
        work_days = max(1, total_days - leave_left)
        return {
            "no_deadline": False,
            "remain_min": remain_min,
            "days_left": total_days,
            "leave_left": leave_left,
            "work_days": work_days,
            "need_per_day": remain_min / work_days,
            "over": total_days <= 0,
        }

    def _gap_text(self):
        g = self._gap()
        if g.get("no_deadline"):
            return "没设目标日 · 点这里设"
        if g.get("over"):
            return f"目标日已过 · 还剩 {g['remain_min']/60:.0f}h"
        need = g["need_per_day"]
        dl = PLAN_DEADLINE[5:].replace("-", "/")      # 07-22 -> 07/22
        if need <= MINUTES_PER_DAY:
            return f"{dl} 截止 · 剩 {g['days_left']} 天 · ✓ 余 {MINUTES_PER_DAY - need:.0f} 分钟/天"
        return f"{dl} 截止 · 剩 {g['days_left']} 天 · ⚠ 需 {need:.0f} 分钟/天"

    def _plan_text(self):
        day_no, total_days, task, quota_min, spent = self._plan()
        short = task[2] if task else "—"
        mpd = max(10, int(MINUTES_PER_DAY or 60))
        # 只算「之前几天」该做而没做的，今天这份还没到点，不算欠账
        behind = (day_no - 1) * mpd - spent
        if behind > 5:
            head = f"第 {day_no} 天 · 欠 {behind} 分钟 · 先补再往前"
        elif behind < -5:
            head = f"第 {day_no} 天 · 提前 {-behind} 分钟 · 今天 {mpd} 分钟"
        else:
            head = f"第 {day_no} 天 · 今天 {mpd} 分钟"
        return f"{head} · {short}"

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
        self.fold_btn = tk.Button(bar, text="—", command=self._minimize, bg="#141618", fg=MUTED,
                                  bd=0, activebackground=LINE, activeforeground=FG,
                                  font=(FONT, 11), cursor="hand2")
        self.fold_btn.pack(side="right", padx=2)
        tk.Label(bar, text=f"v{__version__}", bg="#141618", fg="#4A5056",
                 font=(FONT, 7)).pack(side="right", padx=(0, 6))
        tk.Button(bar, text="API", command=self._open_settings, bg="#141618", fg=ACCENT if aiclient.is_ready(self.cfg) else MUTED,
                  bd=0, activebackground=LINE, activeforeground=FG,
                  font=(FONT, 8, "bold"), cursor="hand2").pack(side="right", padx=(0, 2))
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
        self.today_label = tk.Label(right, text="", bg=BG, fg=ACCENT, font=(FONT, 8),
                                    cursor="hand2")
        self.today_label.pack(anchor="w")
        self.gap_label = tk.Label(right, text="", bg=BG, fg=MUTED, font=(FONT, 8),
                                  cursor="hand2", justify="left")
        self.gap_label.pack(anchor="w")
        for w in (self.today_label, self.gap_label):
            w.bind("<Button-1>", lambda e: self._open_plan())
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
        self.detail_title.pack(fill="x", padx=10, pady=(8, 1))
        self.detail_meta = tk.Label(wrap, text="", bg=CARD, fg="#6E767D",
                                    font=(FONT, 8), anchor="w", justify="left")
        self.detail_meta.pack(fill="x", padx=10, pady=(0, 4))
        self.detail_text = tk.Text(wrap, height=5, bg=CARD, fg=DIM, bd=0,
                                   font=(FONT, 8), wrap="word", cursor="arrow",
                                   highlightthickness=0, padx=0, pady=0,
                                   selectbackground=CARD, spacing1=1, spacing3=3)
        self.detail_text.pack(fill="x", padx=10)
        self.detail_text.bind("<MouseWheel>", self._detail_wheel)

        btns = tk.Frame(wrap, bg=CARD)
        btns.pack(fill="x", padx=6, pady=6)
        for text, color, st in (("✔ 过关", OK, "done"),
                                ("◐ 在途", DOING, "doing"),
                                ("↺ 打回", "#E57373", "todo")):
            tk.Button(btns, text=text, command=lambda s=st: self._set(s),
                      bg=CARD, fg=color, bd=1, relief="flat", highlightbackground=LINE,
                      activebackground=color, activeforeground="#111",
                      font=(FONT, 9, "bold"), cursor="hand2", width=6).pack(side="left", padx=2)
        self.timer_btn = tk.Button(btns, text="▶ 计时", command=self._toggle_timer,
                                   bg=CARD, fg="#BA9BF2", bd=1, relief="flat",
                                   highlightbackground=LINE, activebackground="#BA9BF2",
                                   activeforeground="#111", font=(FONT, 9, "bold"),
                                   cursor="hand2", width=6)
        self.timer_btn.pack(side="left", padx=2)
        self.review_btn = tk.Button(btns, text="AI 批改", command=self._open_review,
                                    bg=CARD, fg=ACCENT, bd=1, relief="flat",
                                    highlightbackground=LINE, activebackground=ACCENT,
                                    activeforeground="#111", font=(FONT, 9, "bold"),
                                    cursor="hand2", width=7)
        self.review_btn.pack(side="left", padx=2)

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
        if getattr(self, "panel", None) is not None:   # 面板打开时先回主视图
            self._close_panel()
            return
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

    # ---------- 弹出面板 ----------
    # 不用 Toplevel：主窗是无边框 + 置顶，永远压在普通窗口上面，
    # 唯一可靠的做法是在同一个窗口里换面板。
    def _show_panel(self, w, h, builder):
        self.body.pack_forget()
        self.panel = tk.Frame(self.root, bg=BG)
        self.panel.pack(fill="both", expand=True)
        self._reposition(w, h)
        builder(self.panel)
        return self.panel

    def _reposition(self, w, h):
        """宽度变了要重新贴右边，否则会顶出屏幕右边缘。"""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(20, sw - w - 36)
        y = max(20, min(self.root.winfo_y(), sh - h - 60))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _close_panel(self):
        panel = getattr(self, "panel", None)
        if panel is not None:
            panel.destroy()
            self.panel = None
        self.body.pack(fill="both", expand=True)
        self._reposition(W, self._target_h())

    # ---------- 任务栏与最小化 ----------
    def _hwnd(self):
        """取顶层窗口句柄。无边框窗口的 winfo_id() 本身就是 HWND。"""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            return hwnd or self.root.winfo_id()
        except Exception:
            return self.root.winfo_id()

    def _enable_taskbar(self):
        """overrideredirect 窗口默认不在任务栏，加 WS_EX_APPWINDOW 才能在任务栏找到它。"""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            self.root.update_idletasks()
            hwnd = self._hwnd()
            u = ctypes.windll.user32
            style = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def _minimize(self):
        """最小化到任务栏。ShowWindow 比 Tk 的 iconify 可靠，无边框窗口也认。"""
        if getattr(self, "panel", None) is not None:
            self._close_panel()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(self._hwnd(), 6)   # SW_MINIMIZE
                return
            except Exception:
                pass
        try:
            self.root.iconify()
        except Exception:
            pass

    # ---------- 计时与学习记录 ----------
    def _toggle_timer(self):
        if self.timer_start is None:
            self.timer_start = datetime.now()
            self.timer_task = self.selected
            self.timer_btn.config(fg=OK)
            self._tick()
        else:
            self._open_session_form()

    def _tick(self):
        if self.timer_start is None:
            return
        secs = int((datetime.now() - self.timer_start).total_seconds())
        m, s = divmod(secs, 60)
        self.timer_btn.config(text=f"■ {m:02d}:{s:02d}")
        self.timer_job = self.root.after(1000, self._tick)

    def _stop_tick(self):
        if self.timer_job:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

    def _cancel_timer(self):
        self.timer_start = None
        self.timer_task = None
        self._stop_tick()
        try:
            self.timer_btn.config(text="▶ 计时", fg="#BA9BF2")
        except Exception:
            pass

    def _open_session_form(self):
        elapsed = 0
        if self.timer_start:
            elapsed = max(1, int((datetime.now() - self.timer_start).total_seconds() // 60))
        tid = self.timer_task or self.selected
        self._show_panel(480, 480, lambda p: self._build_session_panel(p, tid, elapsed))

    def _build_session_panel(self, parent, tid, elapsed):
        _, _, short, full, crit, budget = TASK_BY_ID[tid]
        spent = self._spent_minutes(tid) / 60

        tk.Label(parent, text=f"记录这次学习 · {short}", bg=BG, fg="#BA9BF2",
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(parent, text=f"计时 {elapsed} 分钟（可以改）· 该项已投入 {spent:.1f}h / 预算 {budget:g}h",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", padx=16, pady=(0, 10))

        line = tk.Frame(parent, bg=BG)
        line.pack(fill="x", padx=16)
        tk.Label(line, text="用时", bg=BG, fg=DIM, font=(FONT, 9), width=6,
                 anchor="w").pack(side="left")
        mins = tk.Entry(line, bg=CARD, fg=FG, insertbackground=FG, bd=0, font=(FONT, 9),
                        highlightthickness=1, highlightbackground=LINE,
                        highlightcolor=ACCENT, width=8)
        mins.insert(0, str(elapsed))
        mins.pack(side="left", ipady=4)
        tk.Label(line, text="分钟", bg=BG, fg=MUTED, font=(FONT, 8)).pack(side="left", padx=(6, 0))

        tk.Label(parent, text="这次学到哪 / 卡在哪（写清楚，AI 批改会读它）", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="w", padx=16, pady=(12, 4))
        note = tk.Text(parent, height=7, bg=CARD, fg=FG, insertbackground=FG, bd=0,
                       font=(FONT, 9), wrap="word", padx=10, pady=8, highlightthickness=0)
        note.pack(fill="x", padx=16)
        note.focus_set()

        status = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8), anchor="w")
        status.pack(fill="x", padx=16, pady=(8, 0))

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=16, pady=12)

        def save():
            try:
                m = int(str(mins.get()).strip() or elapsed)
            except ValueError:
                status.config(text="用时要填数字", fg="#E57373")
                return
            if m <= 0:
                status.config(text="用时至少 1 分钟", fg="#E57373")
                return
            text = note.get("1.0", "end").strip()
            if len(text) < 4:
                status.config(text="写一句学到哪，空记录没有意义。", fg="#E57373")
                return
            self.sessions.append({
                "task": tid,
                "start": self.timer_start.isoformat(timespec="minutes") if self.timer_start else "",
                "end": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "minutes": m,
                "note": text,
            })
            self._save()
            self._cancel_timer()
            self._close_panel()
            self._refresh()

        def discard():
            self._cancel_timer()
            self._close_panel()
            self._refresh()

        tk.Button(row, text="保存记录", command=save, bg=CARD, fg=OK, bd=1, relief="flat",
                  highlightbackground=LINE, activebackground=OK, activeforeground="#111",
                  font=(FONT, 9, "bold"), cursor="hand2", width=10).pack(side="left")
        tk.Button(row, text="放弃这次", command=discard, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=10).pack(side="left", padx=(8, 0))

    # ---------- 语音输入 ----------
    def _listen_once(self, on_text):
        """调 Windows 离线语音引擎识别一句。on_text 收到文本，空串表示没听清。"""
        if sys.platform != "win32":
            on_text("")
            return
        ps = (
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
            "Add-Type -AssemblyName System.Speech;"
            "$r=New-Object System.Speech.Recognition.SpeechRecognitionEngine;"
            "$r.SetInputToDefaultAudioDevice();"
            "$r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));"
            "$r.InitialSilenceTimeout=[TimeSpan]::FromSeconds(6);"
            "$r.EndSilenceTimeout=[TimeSpan]::FromSeconds(1.5);"
            "$res=$r.Recognize();"
            "if($res){[Console]::Out.Write($res.Text)}"
        )

        def worker():
            txt = ""
            try:
                import subprocess
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-STA", "-Command", ps],
                    capture_output=True, timeout=40,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                txt = (out.stdout or b"").decode("utf-8", "replace").strip()
            except Exception:
                txt = ""
            self.root.after(0, lambda t=txt: on_text(t))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- 计划设置 ----------
    def _open_plan(self):
        self._show_panel(500, 545, self._build_plan_panel)

    def _write_plan(self):
        global PLAN_START, PLAN_DEADLINE, MINUTES_PER_DAY, LEAVE_DAYS
        try:
            raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        raw["plan"] = {"start": PLAN_START, "deadline": PLAN_DEADLINE,
                       "minutes_per_day": MINUTES_PER_DAY,
                       "leave_days": sorted(set(LEAVE_DAYS))}
        TASKS_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_plan_panel(self, parent):
        global PLAN_DEADLINE, MINUTES_PER_DAY, LEAVE_DAYS
        today = datetime.now().strftime("%Y-%m-%d")
        today_d = datetime.now().date()

        tk.Label(parent, text="计划设置", bg=BG, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent, text="改完点保存。今天想多做就调高每日配额，做不动就请假——请假的日子不算欠账。",
                 bg=BG, fg=MUTED, font=(FONT, 8), wraplength=460,
                 justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        # 每日配额
        row1 = tk.Frame(parent, bg=BG)
        row1.pack(fill="x", padx=16)
        tk.Label(row1, text="每天", bg=BG, fg=DIM, font=(FONT, 9), width=5,
                 anchor="w").pack(side="left")
        mpd_var = tk.StringVar(value=str(MINUTES_PER_DAY))
        mpd_entry = tk.Entry(row1, textvariable=mpd_var, bg=CARD, fg=FG, insertbackground=FG,
                             bd=0, font=(FONT, 9), highlightthickness=1,
                             highlightbackground=LINE, highlightcolor=ACCENT, width=6)
        mpd_entry.pack(side="left", ipady=4)
        tk.Label(row1, text="分钟", bg=BG, fg=MUTED, font=(FONT, 8)).pack(side="left", padx=(6, 10))

        def set_mpd(v):
            mpd_var.set(str(v))

        for v in (30, 45, 60, 90, 120):
            tk.Button(row1, text=str(v), command=lambda x=v: set_mpd(x), bg=CARD, fg=DIM,
                      bd=1, relief="flat", highlightbackground=LINE, activebackground=ACCENT,
                      activeforeground="#111", font=(FONT, 8), cursor="hand2",
                      width=3).pack(side="left", padx=1)

        # 目标完成日
        row2 = tk.Frame(parent, bg=BG)
        row2.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(row2, text="目标日", bg=BG, fg=DIM, font=(FONT, 9), width=5,
                 anchor="w").pack(side="left")
        dl_var = tk.StringVar(value=PLAN_DEADLINE or "")
        dl_entry = tk.Entry(row2, textvariable=dl_var, bg=CARD, fg=FG, insertbackground=FG,
                            bd=0, font=(FONT, 9), highlightthickness=1,
                            highlightbackground=LINE, highlightcolor=ACCENT, width=14)
        dl_entry.pack(side="left", ipady=4)
        tk.Label(row2, text="格式 2027-05-22", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(8, 0))

        # 请假
        row3 = tk.Frame(parent, bg=BG)
        row3.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(row3, text="请假", bg=BG, fg=DIM, font=(FONT, 9), width=5,
                 anchor="w").pack(side="left")
        leave_var = tk.Label(row3, text="", bg=BG, fg=DOING, font=(FONT, 8))
        leave_var.pack(side="left")

        tip = tk.Label(parent, text="", bg=BG, fg=DIM, font=(FONT, 8), wraplength=460,
                       justify="left", anchor="w")
        tip.pack(anchor="w", padx=16, pady=(10, 0))

        def read_vals():
            try:
                mpd = max(10, int(str(mpd_var.get()).strip() or 0))
            except ValueError:
                mpd = 60
            dl = str(dl_var.get()).strip()
            if dl:
                try:
                    datetime.strptime(dl, "%Y-%m-%d")
                except ValueError:
                    return None, None, "目标日格式要写成 2027-05-22"
            return mpd, dl, None

        def preview(*_):
            mpd, dl, err = read_vals()
            if err:
                tip.config(text=err, fg="#E57373")
                return
            remain = sum(t[5] * 60 for t in TASKS if t[5]
                         and self.state.get(t[0], {}).get("state") != "done")
            if not dl:
                tip.config(text=f"没设目标日。剩余 {remain/60:.0f} 小时，按每天 {mpd} 分钟约 "
                                f"{-(-int(remain)//mpd)} 天完成。", fg=MUTED)
                return
            deadline = datetime.strptime(dl, "%Y-%m-%d").date()
            if deadline < today_d:
                tip.config(text="目标日已经过去了。", fg="#E57373")
                return
            total = (deadline - today_d).days + 1
            leave_n = sum(1 for d in LEAVE_DAYS
                          if today_d <= datetime.strptime(d, "%Y-%m-%d").date() <= deadline)
            work = max(1, total - leave_n)
            need = remain / work
            ok = "✓ 来得及" if need <= mpd else f"⚠ 差 {need - mpd:.0f} 分钟/天"
            tip.config(text=f"剩 {total} 天，扣除请假 {leave_n} 天 → 实际 {work} 个学习日。\n"
                            f"还剩 {remain/60:.0f} 小时，需 {need:.0f} 分钟/天。{ok}",
                       fg=OK if need <= mpd else "#E57373")

        def refresh_leave():
            today_in = today in LEAVE_DAYS
            for w in row3.winfo_children()[2:]:
                w.destroy()
            tk.Button(row3, text=("取消今天请假" if today_in else "今天请假"),
                      command=lambda: toggle_today(), bg=CARD,
                      fg=(MUTED if today_in else DOING), bd=1, relief="flat",
                      highlightbackground=LINE, activebackground=LINE,
                      activeforeground=FG, font=(FONT, 8), cursor="hand2",
                      width=12).pack(side="left", padx=(0, 6))
            for d in sorted(LEAVE_DAYS):
                tk.Button(row3, text=f"{d} ✕", command=lambda x=d: drop_leave(x), bg=CARD,
                          fg=MUTED, bd=0, relief="flat", highlightbackground=LINE,
                          activebackground="#8B3A3A", activeforeground="white",
                          font=(FONT, 7), cursor="hand2").pack(side="left", padx=1)
            preview()

        def toggle_today():
            if today in LEAVE_DAYS:
                LEAVE_DAYS.remove(today)
            else:
                LEAVE_DAYS.append(today)
            refresh_leave()

        def drop_leave(d):
            if d in LEAVE_DAYS:
                LEAVE_DAYS.remove(d)
            refresh_leave()

        # 绑变量而不是按键：粘贴、自动填充也能触发预览
        mpd_var.trace_add("write", lambda *_: preview())
        dl_var.trace_add("write", lambda *_: preview())
        refresh_leave()

        status = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8), anchor="w")
        status.pack(fill="x", padx=16, pady=(8, 0))

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=16, pady=10)

        def save():
            mpd, dl, err = read_vals()
            if err:
                status.config(text=err, fg="#E57373")
                return
            MINUTES_PER_DAY, PLAN_DEADLINE = mpd, dl
            self._write_plan()
            status.config(text="已保存", fg=OK)
            self._close_panel()
            self._refresh()

        tk.Button(row, text="保存", command=save, bg=CARD, fg=OK, bd=1, relief="flat",
                  highlightbackground=LINE, activebackground=OK, activeforeground="#111",
                  font=(FONT, 9, "bold"), cursor="hand2", width=9).pack(side="left")
        tk.Button(row, text="返回", command=self._close_panel, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=8).pack(side="right")

    def _open_review(self):
        _, _, short, full, crit, _h = TASK_BY_ID[self.selected]
        self._show_panel(520, 700, lambda p: self._build_review_panel(p, short, full, crit))

    def _build_review_panel(self, parent, short, full, crit):
        tk.Label(parent, text=f"AI 批改 · {short}", bg=BG, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(parent, text="贴汇报 / 推导过程，AI 按这项的验收标准判一次", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="w", padx=14, pady=(0, 6))

        inp = tk.Text(parent, height=9, bg=CARD, fg=FG, insertbackground=FG, bd=0,
                      font=(FONT, 9), wrap="word", padx=10, pady=8, highlightthickness=0)
        inp.pack(fill="x", padx=14)
        placeholder = ("例：行优先 LOC(i,j) = base + ((i-1)×n + (j-1))×L，"
                       "因为第 i 行之前有 (i-1) 整行、每行 n 个元素。\n"
                       "自证：A[1..8][1..10]，LOC(5,7) = 1000 + (4×10+6)×4 = 1184。")
        inp.insert("1.0", placeholder)
        inp.config(fg=MUTED)

        def clear_placeholder(_=None):
            if str(inp.cget("fg")) == MUTED:
                inp.delete("1.0", "end")
                inp.config(fg=FG)

        inp.bind("<FocusIn>", clear_placeholder)
        inp.bind("<Button-1>", clear_placeholder, add="+")

        picked = []          # {"kind":"image","b64","mime","name"} 或 {"kind":"file","path"}

        status = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8),
                          anchor="w", justify="left", wraplength=470)
        status.pack(fill="x", padx=14, pady=(6, 0))

        file_row = tk.Frame(parent, bg=BG)
        file_row.pack(fill="x", padx=14, pady=(6, 0))
        file_label = tk.Label(file_row, text="截图后 Ctrl+V 粘图 · 也可用语音说你的推导",
                              bg=BG, fg=MUTED, font=(FONT, 8), anchor="w",
                              justify="left", wraplength=280)
        file_label.pack(side="left", fill="x", expand=True)

        def start_speech():
            speak_btn.config(state="disabled", text="听…")
            status.config(text="正在听，说完停顿一下会自动结束（第一次会要麦克风权限）", fg=DOING)

            def got(txt):
                speak_btn.config(state="normal", text="语音输入")
                if not txt:
                    status.config(text="没听清。靠近麦克风再说一次，或按 Win+H 用系统语音输入",
                                  fg="#E57373")
                    return
                clear_placeholder()
                cur = inp.get("1.0", "end").strip()
                inp.insert("end", ("\n" if cur else "") + txt)
                inp.see("end")
                status.config(text=f"听写：{txt[:50]}", fg=OK)

            self._listen_once(got)

        speak_btn = tk.Button(file_row, text="语音输入", command=start_speech, bg=CARD,
                              fg="#BA9BF2", bd=1, relief="flat", highlightbackground=LINE,
                              activebackground="#BA9BF2", activeforeground="#111",
                              font=(FONT, 8, "bold"), cursor="hand2", width=9)
        speak_btn.pack(side="left", padx=(0, 6), before=file_label)

        def refresh_label():
            if not picked:
                file_label.config(text="截图后 Ctrl+V 粘图 · 也可用语音说你的推导", fg=MUTED)
                return
            imgs = sum(1 for x in picked if x["kind"] == "image")
            parts = []
            if imgs:
                parts.append(f"{imgs} 张图")
            files = [x["path"] for x in picked if x["kind"] == "file"]
            if files:
                shown = "、".join(Path(p).name for p in files[:2])
                parts.append(shown + (f" 等 {len(files)} 个文件" if len(files) > 2 else ""))
            file_label.config(text="已选：" + "、".join(parts), fg=ACCENT)

        def pick_files():
            paths = filedialog.askopenfilenames(
                parent=parent, title="选图片或文本文件",
                filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp"),
                           ("文本 / 代码", "*.txt *.md *.py *.c *.cpp *.h *.java *.cs *.json *.csv"),
                           ("全部文件", "*.*")])
            for p in paths:
                if not any(x.get("path") == p for x in picked):
                    picked.append({"kind": "file", "path": p})
            refresh_label()

        def paste(_=None):
            """优先按图片粘；剪贴板里没有图就放行，走正常文本粘贴。"""
            clear_placeholder()
            try:
                img = clipimg.grab_image(self.root)
            except Exception as e:
                status.config(text=f"读剪贴板失败：{e}", fg="#E57373")
                return None
            if img:
                picked.append({"kind": "image", "b64": img["b64"],
                               "mime": img["mime"], "name": img["name"]})
                refresh_label()
                status.config(text=f"已粘入剪贴板图片（{img['bytes'] // 1024} KB）", fg=OK)
                return "break"
            try:
                files = clipimg.clipboard_files()
            except Exception:
                files = []
            if files:
                added = 0
                for p in files:
                    if not any(x.get("path") == p for x in picked):
                        picked.append({"kind": "file", "path": p})
                        added += 1
                refresh_label()
                if added:
                    status.config(text=f"已粘入 {added} 个文件", fg=OK)
                    return "break"
            return None

        tk.Button(file_row, text="＋ 添加", command=pick_files, bg=CARD, fg=ACCENT, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=ACCENT,
                  activeforeground="#111", font=(FONT, 8, "bold"), cursor="hand2",
                  width=7).pack(side="right")

        inp.bind("<Control-v>", paste)
        inp.bind("<Control-V>", paste)

        out = tk.Text(parent, height=11, bg=CARD, fg=DIM, bd=0, font=(FONT, 9), wrap="word",
                      padx=10, pady=8, highlightthickness=0, state="disabled")
        out.pack(fill="both", expand=True, padx=14, pady=(6, 0))

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=14, pady=10)

        def done(text, err=None):
            btn.config(state="normal", text="提交批改")
            out.config(state="normal")
            out.delete("1.0", "end")
            if err:
                status.config(text="调用失败", fg="#E57373")
                out.insert("end", err)
            else:
                verdict = "🟢" if "🟢" in text else ("🟡" if "🟡" in text else ("🔴" if "🔴" in text else "—"))
                status.config(text=f"批改完成 {verdict} · 是否过关仍由你决定", fg=OK)
                out.insert("end", text)
            out.config(state="disabled")

        def submit():
            report = "" if str(inp.cget("fg")) == MUTED else inp.get("1.0", "end").strip()
            if len(report) < 10 and not picked:
                status.config(text="汇报太短了。写清过程，或者加一张手写推导的照片。", fg="#E57373")
                return
            if not aiclient.is_ready(self.cfg):
                status.config(text="还没配 API Key。点标题栏的 API 按钮填一个。", fg=DOING)
                return

            images, texts = [], []
            for item in picked:
                if item["kind"] == "image":
                    images.append({"b64": item["b64"], "mime": item["mime"],
                                   "name": item.get("name") or "图片"})
                    continue
                try:
                    kind, data = aiclient.read_attachment(item["path"])
                except Exception as e:
                    status.config(text=str(e), fg="#E57373")
                    return
                if kind == "image":
                    images.append(data)
                else:
                    texts.append(f"【附件 {Path(item['path']).name}】\n{data}")
            if texts:
                report = (report + "\n\n" + "\n\n".join(texts)).strip()

            btn.config(state="disabled", text="批改中…")
            status.config(text=f"已发出（{len(images)} 张图）等模型回…", fg=DOING)
            def worker():
                try:
                    text = aiclient.review(self.cfg, full, crit, report,
                                           attachments=images or None,
                                           sessions=self._recent_sessions(self.selected))
                    self.root.after(0, lambda t=text: done(t))
                except Exception as e:
                    self.root.after(0, lambda m=str(e): done(None, m))

            threading.Thread(target=worker, daemon=True).start()

        btn = tk.Button(row, text="提交批改", command=submit, bg=CARD, fg=ACCENT, bd=1,
                        relief="flat", highlightbackground=LINE, activebackground=ACCENT,
                        activeforeground="#111", font=(FONT, 9, "bold"), cursor="hand2", width=10)
        btn.pack(side="left")
        tk.Button(row, text="返回", command=self._close_panel, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=8).pack(side="right")

    # ---------- API 设置 ----------
    def _open_settings(self):
        self._show_panel(560, 470, self._build_settings_panel)

    def _build_settings_panel(self, parent):
        fields = {}

        tk.Label(parent, text="API 设置", bg=BG, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent, text="填一次就存在本地 config.json，不会上传到任何地方",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", padx=16, pady=(0, 8))

        form = tk.Frame(parent, bg=BG)
        form.pack(fill="x", padx=16)
        form.columnconfigure(1, weight=1)

        def add_row(r, label, key, show=None):
            tk.Label(form, text=label, bg=BG, fg=DIM, font=(FONT, 9),
                     anchor="w", width=10).grid(row=r, column=0, sticky="w", pady=5)
            e = tk.Entry(form, bg=CARD, fg=FG, insertbackground=FG, bd=0, font=(FONT, 9),
                         highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
            if show:
                e.config(show=show)
            e.grid(row=r, column=1, sticky="ew", padx=(4, 4), ipady=4)
            fields[key] = e
            return e

        pvar = tk.StringVar(value=self.cfg.get("provider") or "deepseek")
        tk.Label(form, text="服务商", bg=BG, fg=DIM, font=(FONT, 9), anchor="w",
                 width=10).grid(row=0, column=0, sticky="w", pady=5)
        style = ttk.Style()
        try:
            style.theme_use("clam")          # 只有 clam 主题能改下拉框底色
            style.configure("Dark.TCombobox", fieldbackground=CARD, background=CARD,
                            foreground=FG, arrowcolor=FG, bordercolor=LINE,
                            selectbackground=CARD, selectforeground=FG)
            style.map("Dark.TCombobox",
                      fieldbackground=[("readonly", CARD)],
                      foreground=[("readonly", FG)],
                      background=[("readonly", CARD)])
        except Exception:
            pass
        combo = ttk.Combobox(form, textvariable=pvar, style="Dark.TCombobox", state="readonly",
                             values=[f"{k} · {v['name']}" for k, v in aiclient.PROVIDERS.items()],
                             font=(FONT, 9))
        combo.grid(row=0, column=1, sticky="ew", padx=(4, 4), pady=5)

        add_row(1, "base_url", "base_url")
        add_row(2, "model", "model")
        key_entry = add_row(3, "api_key", "api_key", show="*")
        add_row(4, "proxy", "proxy")

        for k in ("base_url", "model", "api_key", "proxy"):
            fields[k].insert(0, str(self.cfg.get(k) or ""))

        tip = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8),
                       anchor="w", justify="left", wraplength=520)
        tip.pack(fill="x", padx=16, pady=(10, 0))

        def provider_key():
            return pvar.get().split(" · ")[0]

        def sync_tip(*_):
            p = aiclient.PROVIDERS.get(provider_key(), {})
            tip.config(text=f"申请地址：{p.get('apply') or '自填'}    费用：{p.get('cost') or '—'}")

        def on_provider(*_):
            p = aiclient.PROVIDERS.get(provider_key(), {})
            for k in ("base_url", "model"):
                if p.get(k):
                    fields[k].delete(0, "end")
                    fields[k].insert(0, p[k])
            sync_tip()

        combo.bind("<<ComboboxSelected>>", on_provider)
        sync_tip()

        status = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8),
                          anchor="w", justify="left", wraplength=520)
        status.pack(fill="x", padx=16, pady=(8, 0))

        def collect():
            return {"provider": provider_key(), "base_url": fields["base_url"].get().strip(),
                    "model": fields["model"].get().strip(), "api_key": fields["api_key"].get().strip(),
                    "proxy": fields["proxy"].get().strip()}

        def save():
            cfg = dict(self.cfg)
            cfg.update(collect())
            try:
                path = aiclient.save_config(APP_DIR, cfg)
            except Exception as e:
                status.config(text=f"保存失败：{e}", fg="#E57373")
                return
            self.cfg = cfg
            status.config(text=f"已保存 → {path}", fg=OK)

        def test():
            cfg = dict(self.cfg)
            cfg.update(collect())
            status.config(text="测试中…", fg=DOING)

            def worker():
                try:
                    msg = aiclient.test_connection(cfg)
                    self.root.after(0, lambda: status.config(text=msg, fg=OK))
                except Exception as e:
                    self.root.after(0, lambda m=str(e): status.config(text=m, fg="#E57373"))
            threading.Thread(target=worker, daemon=True).start()

        def toggle_key():
            key_entry.config(show="" if key_entry.cget("show") else "*")

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=16, pady=(12, 10))
        for text, cmd, color in (("保存", save, OK), ("测试连接", test, ACCENT)):
            tk.Button(row, text=text, command=cmd, bg=CARD, fg=color, bd=1, relief="flat",
                      highlightbackground=LINE, activebackground=color, activeforeground="#111",
                      font=(FONT, 9, "bold"), cursor="hand2", width=9).pack(side="left", padx=(0, 6))
        tk.Button(row, text="显示 Key", command=toggle_key, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=9).pack(side="left")
        tk.Button(row, text="返回", command=self._close_panel, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=8).pack(side="right")

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
        plan_txt = self._plan_text()
        self.today_label.config(text=plan_txt, fg=DOING if "欠" in plan_txt else ACCENT)
        gap_txt = self._gap_text()
        self.gap_label.config(text=gap_txt,
                              fg="#E57373" if ("⚠" in gap_txt or "已过" in gap_txt) else MUTED)
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
        spent = self._spent_minutes(self.selected) / 60
        cnt = sum(1 for s in self.sessions if s.get("task") == self.selected)
        self.detail_meta.config(
            text=f"已投入 {spent:.1f}h / 预算 {hours:g}h · {cnt} 次学习记录" if cnt
            else f"还没记录过学习过程 · 预算 {hours:g}h · 点「▶ 计时」开始")
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
    root.after(50, app._after_show)
    if not STATE_FILE.exists():
        app._save()
    if "--smoke" in sys.argv:
        root.after(800, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
