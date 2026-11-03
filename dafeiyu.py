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
import os
import sys
from datetime import datetime
from pathlib import Path

import tkinter as tk


__version__ = "1.2.0"

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
    ("ds1b", "数据结构", "串与模式匹配", "第四章第二节：串（课件 p885-927，43 页）", [
        "串的基本概念：空串 \"\" 与空白串 \" \" 的区别，长度怎么数",
        "朴素匹配（BF）：失配后主串指针回溯到哪，最坏复杂度 O(n×m)",
        "KMP：说清为什么主串指针不用回溯，i 不回退、j 退到 next[j]",
        "手算 next 数组：给任意模式串能推出 next",
        "next 与 nextval 的区别，什么情况下 nextval 更优",
        "限时测：模式匹配 10 题 ≥85（课程标注的本章两个难点之一）",
    ]),
    ("ds2", "数据结构", "树与二叉树", "树与二叉树（遍历、性质）", [
        "三种遍历手写互推，不查表不卡顿",
        "由两种遍历序列还原唯一二叉树，10 题全对",
        "完全二叉树父子下标公式默写 + 节点数性质推导",
        "树/森林/二叉树相互转换画图正确",
        "手写非递归遍历代码并跑通输出",
    ]),
    ("ds2b", "数据结构", "哈夫曼树与编码", "第五节 哈夫曼树及哈夫曼编码（课件 p1211-1259，49 页，课程标注的本章难点）", [
        "构造哈夫曼树：给权值集合能画出完整合并过程，不查表",
        "WPL 计算：会算加权路径长度，且能说明它为什么最优",
        "哈夫曼编码：按左 0 右 1 写出每个字符的编码",
        "前缀编码的含义：为什么哈夫曼编码一定是前缀编码",
        "编码压缩率计算：给原文长度和编码表，算出压缩后多少位",
        "限时测：哈夫曼 8 题 ≥85",
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
    ("dm1", "离散数学", "命题与命题公式", "第一章 命题与命题公式", [
        "命题判定：能判断一句话是否为命题（陈述句 + 唯一真值）",
        "五个联结词：¬ ∧ ∨ → ↔ 的符号化，各做 3 题",
        "真值表：给定公式能构造真值表，判断重言式/矛盾式/可满足式",
        "等值演算：熟记常用命题定律与蕴含式，会化简公式",
        "联结词完备集：知道 {¬,∧} 和 {¬,∨} 是最小完备集",
    ]),
    ("dm2", "离散数学", "命题逻辑推理", "第二章 命题逻辑的推理理论", [
        "范式：能求给定公式的析取范式与合取范式",
        "主范式：主析取 / 主合取范式，会求成真赋值成假赋值的编码",
        "P 规则、T 规则、CP 规则：各做 3 道推理证明题",
        "间接证法：附加前提法（反证法）与 CP 规则的区别",
    ]),
    ("dm3", "离散数学", "谓词逻辑", "第三章 谓词逻辑", [
        "谓词、个体词、命题函数的概念，能用谓词表示命题",
        "量词：全称 ∀ 与存在 ∃，能判断辖域、指导变元、自由/约束出现",
        "改名规则与代入规则，各做 2 题",
        "谓词演算的等值式与蕴含式，熟记",
        "前束范式：能把公式化为前束范式",
    ]),
    ("dm4", "离散数学", "集合", "第四章 集合", [
        "集合运算：并、交、差、补、对称差，各做 2 题",
        "幂集：求给定集合的幂集，知道 |P(A)| = 2^|A|",
        "笛卡尔积：会求 A×B 并知道元素个数",
        "可数集与不可数集、基数的比较（领会层次）",
    ]),
    ("dm5", "离散数学", "关系与函数", "第五章 关系与函数", [
        "关系三种表示：集合、关系矩阵、关系图，能互转",
        "五个性质判定：自反、反自反、对称、反对称、传递，各做 3 题",
        "复合关系与关系矩阵的布尔运算",
        "三种闭包：自反、对称、传递闭包，会求",
        "等价关系与划分：能判定、能求等价类",
        "偏序关系与哈斯图：能画图，求极大/极小/最大/最小元",
        "函数：单射、满射、双射判定，复合函数计算",
    ]),
    ("dm6", "离散数学", "代数系统", "第六章 代数系统的一般概念", [
        "代数系统与运算性质（封闭、交换、结合、分配、吸收）",
        "单位元、零元、逆元：能判断并求出",
        "半群、独异点、群的定义与判定",
        "群的阶、元素的阶，能计算",
        "子群判定，循环群与生成元",
        "环与域的概念与判定",
    ]),
    ("dm7", "离散数学", "格与布尔代数", "第七章 格与布尔代数", [
        "格的定义与判定（偏序格 / 代数格两种等价定义）",
        "分配格、有补格、有界格：能判定并求补元",
        "布尔代数：定义与性质，能验证布尔恒等式",
        "布尔函数与布尔表达式（领会层次）",
    ]),
    ("dm8", "离散数学", "图", "第八章 图", [
        "图的基本概念：有向/无向、度、握手定理、子图、补图",
        "通路与回路：连通性判定，强/弱/单向连通",
        "图的矩阵表示：邻接矩阵、可达矩阵",
        "欧拉图：判定条件（全是偶度点 / 恰两个奇度点）",
        "哈密顿图：判定条件与常见反例",
    ]),
    ("dm9", "离散数学", "图的应用", "第九章 图的应用", [
        "树的定义与性质：m = n-1，无回路且连通",
        "生成树与最小生成树：Kruskal / Prim 手算一遍",
        "根树、二叉树，树的遍历与表达式表示",
        "二部图与匹配（领会层次）",
        "平面图与欧拉公式 v - e + f = 2",
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
    "ds0": 8.5, "ds1": 6.5, "ds1b": 2.5, "ds2": 8.5, "ds2b": 2.5, "ds3": 7.8, "ds4": 9.6, "ds5": 14,
    # 软考网工已按希赛录播实测校正：2659 分钟 / 1.5 倍速 / 含消化
    "ne1": 7.6, "ne2": 14.5, "ne3": 19.9, "ne4": 24.4, "ne5": 22,
    # 离散数学：按自考大纲九章拆分，总量 32h 为经验值，待视频时长校准
    "dm1": 4.0, "dm2": 3.5, "dm3": 3.0, "dm4": 1.5, "dm5": 5.5,
    "dm6": 5.5, "dm7": 3.5, "dm8": 3.0, "dm9": 2.5,
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
        self.timer = None          # 落盘用：{"task":..., "start":...}
        self.timer_start = None
        self.timer_task = None
        self.timer_job = None
        self.load_error = ""
        self.state = self._load()
        self._restore_timer()
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
        if self.load_error:
            self.today_label.config(text="⚠ " + self.load_error, fg="#E57373")
        if self.timer_start is not None:
            self.timer_btn.config(fg=OK)
            self._tick()
            self.selected = self.timer_task or self.selected

    # ---------- 持久化 ----------
    def _empty_state(self):
        return {tid: {"state": "todo", "ts": ""} for tid, *_ in TASKS}

    def _load(self):
        """读账本。文件坏了先备份再回退，绝不静默丢掉用户的进度。"""
        self.sessions = []
        if not STATE_FILE.exists():
            return self._empty_state()
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("账本根节点不是对象")
        except Exception as e:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = STATE_FILE.with_name(f"{STATE_FILE.name}.broken-{stamp}")
            try:
                STATE_FILE.replace(backup)
                self.load_error = f"账本读不了，已备份为 {backup.name}，进度从零开始"
            except Exception:
                self.load_error = f"账本读不了且备份失败：{e}"
            return self._empty_state()

        data = raw.get("tasks")
        if not isinstance(data, dict):
            data = {}
        self.sessions = [x for x in (raw.get("sessions") or []) if isinstance(x, dict)]
        t = raw.get("timer")
        self.timer = t if isinstance(t, dict) and t.get("start") else None
        state = {}
        for tid, *_ in TASKS:
            rec = data.get(tid)
            if isinstance(rec, dict) and rec.get("state") in ("todo", "doing", "done"):
                state[tid] = {"state": rec["state"], "ts": rec.get("ts") or ""}
            else:
                state[tid] = {"state": "todo", "ts": ""}
        return state

    def _save(self):
        """原子写：先写 .tmp 再 os.replace，写一半断电也不会毁掉账本。"""
        payload = json.dumps({
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tasks": self.state,
            "sessions": self.sessions,
            "timer": self.timer,
        }, ensure_ascii=False, indent=2)
        tmp = STATE_FILE.with_suffix(".tmp")
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, STATE_FILE)
        except Exception:
            try:
                STATE_FILE.write_text(payload, encoding="utf-8")
            except Exception:
                pass

    def _restore_timer(self):
        """上次没结束的计时，12 小时内自动续上。"""
        if not self.timer:
            return
        try:
            st = datetime.fromisoformat(self.timer["start"])
        except Exception:
            self.timer = None
            return
        if (datetime.now() - st).total_seconds() > 12 * 3600:
            self.timer = None
            return
        self.timer_start = st
        self.timer_task = self.timer.get("task")

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
        # 日历只安排还没过关的：已过关的不再占天数
        todo = [t for t in TASKS if t[5] and self.state.get(t[0], {}).get("state") != "done"]
        total_min = sum(t[5] * 60 for t in todo)
        if total_min <= 0:
            return 1, 1, None, mpd, 0
        total_days = max(1, -(-int(total_min) // mpd))       # 向上取整
        day_no = (datetime.now().date() - start).days + 1
        if day_no < 1:
            day_no = 1
        quota_min = day_no * mpd
        spent = sum(int(s.get("minutes") or 0) for s in self.sessions)

        # 定位今天配额落在哪一项
        acc = 0
        pick = todo[0] if todo else None
        for t in todo:
            tmin = t[5] * 60
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
        self.detail_meta = tk.Label(wrap, text="", bg=CARD, fg="#8A939B",
                                    font=(FONT, 8), anchor="w", justify="left",
                                    cursor="hand2")
        self.detail_meta.pack(fill="x", padx=10, pady=(0, 4))
        self.detail_meta.bind("<Button-1>", lambda e: self._open_sessions())
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

    # ---------- 查看学习记录 ----------
    def _open_sessions(self):
        tid = self.selected
        _, _, short, full, crit, hours = TASK_BY_ID[tid]
        self._show_panel(540, 640, lambda p: self._build_sessions_panel(p, tid, short, full, hours))

    def _build_sessions_panel(self, parent, tid, short, full, budget):
        rows = [x for x in self.sessions if x.get("task") == tid]
        total = sum(int(x.get("minutes") or 0) for x in rows)

        tk.Label(parent, text=f"学习记录 · {short}", bg=BG, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent,
                 text=f"共 {len(rows)} 次 · 累计 {total // 60} 小时 {total % 60} 分 · 预算 {budget:g}h",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", padx=16, pady=(0, 8))

        bar = tk.Canvas(parent, height=6, bg=CARD, highlightthickness=0)
        bar.pack(fill="x", padx=16, pady=(0, 10))
        if budget > 0:
            pct = min(1.0, (total / 60) / budget)

        def draw(*_):
            w = max(bar.winfo_width(), 1)
            bar.delete("all")
            bar.create_rectangle(0, 0, w, 6, fill=CARD, width=0)
            if budget > 0:
                bar.create_rectangle(0, 0, w * min(1.0, (total / 60) / budget), 6, fill=ACCENT, width=0)

        bar.bind("<Configure>", draw)

        # 按钮行必须先占住底部，否则会被下面 expand=True 的 Text 挤出窗口
        row = tk.Frame(parent, bg=BG)
        row.pack(side="bottom", fill="x", padx=16, pady=(0, 12))
        tk.Label(row, text="存在 dafeiyu_state.json 的 sessions 里", bg=BG, fg="#5C646B",
                 font=(FONT, 7)).pack(side="left")
        tk.Button(row, text="返回", command=self._close_panel, bg=CARD, fg=MUTED, bd=1,
                  relief="flat", highlightbackground=LINE, activebackground=LINE,
                  activeforeground=FG, font=(FONT, 9), cursor="hand2",
                  width=8).pack(side="right")

        body = tk.Text(parent, bg=CARD, fg="#C9CFD6", bd=0, font=(FONT, 9), wrap="word",
                       padx=12, pady=10, highlightthickness=0, state="normal")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        if not rows:
            body.insert("end", "还没有记录。\n\n点「▶ 计时」开始学，结束后填两行，这里就会出现。")
        else:
            for x in reversed(rows):
                body.insert("end", f'{x.get("end") or "—"}    {x.get("minutes")} 分钟\n')
                body.insert("end", f'  {x.get("note") or "（没写内容）"}\n\n')
        body.config(state="disabled")

    # ---------- 语音输入 ----------
    def _listen_once(self, on_text):
        """调 Windows 自带离线引擎识别一句。on_text 收到文本，空串表示没听清。"""
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
            import subprocess
            import threading as _th
            txt = ""
            try:
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-STA", "-Command", ps],
                    capture_output=True, timeout=40,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                txt = (out.stdout or b"").decode("utf-8", "replace").strip()
            except Exception:
                txt = ""
            self.root.after(0, lambda t=txt: on_text(t))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 计时与学习记录 ----------
    def _toggle_timer(self):
        if self.timer_start is None:
            self.timer_start = datetime.now()
            self.timer_task = self.selected
            self.timer = {"task": self.timer_task,
                          "start": self.timer_start.isoformat(timespec="seconds")}
            self._save()          # 立刻落盘：关窗/断电也不丢这段计时
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
        self.timer = None
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

        lab_row = tk.Frame(parent, bg=BG)
        lab_row.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(lab_row, text="这次学到哪 / 卡在哪", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="left")
        note = tk.Text(parent, height=7, bg=CARD, fg=FG, insertbackground=FG, bd=0,
                       font=(FONT, 9), wrap="word", padx=10, pady=8, highlightthickness=0)
        note.pack(fill="x", padx=16)
        note.focus_set()

        def start_speech():
            speak_btn.config(state="disabled", text="听…")
            status.config(text="正在听，说完停顿一下自动结束（首次会要麦克风权限）", fg=DOING)

            def got(txt):
                speak_btn.config(state="normal", text="语音输入")
                if not txt:
                    status.config(text="没听清。靠近麦克风再说一次，或按 Win+H", fg="#E57373")
                    return
                cur = note.get("1.0", "end").strip()
                note.insert("end", ("\n" if cur else "") + txt)
                note.see("end")
                status.config(text=f"听写：{txt[:46]}", fg=OK)

            self._listen_once(got)

        speak_btn = tk.Button(lab_row, text="语音输入", command=start_speech, bg=CARD,
                              fg="#BA9BF2", bd=1, relief="flat", highlightbackground=LINE,
                              activebackground="#BA9BF2", activeforeground="#111",
                              font=(FONT, 8, "bold"), cursor="hand2", width=9)
        speak_btn.pack(side="right")

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
            self._cancel_timer()   # 先清计时，再落盘
            self._save()
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

    # ---------- 计划设置 ----------
    def _open_plan(self):
        self._show_panel(460, 370, self._build_plan_panel)

    def _write_plan(self):
        global PLAN_START, PLAN_DEADLINE, MINUTES_PER_DAY
        try:
            raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        raw["plan"] = {"start": PLAN_START, "deadline": PLAN_DEADLINE,
                       "minutes_per_day": MINUTES_PER_DAY}
        TASKS_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_plan_panel(self, parent):
        global PLAN_DEADLINE, MINUTES_PER_DAY
        today_d = datetime.now().date()

        tk.Label(parent, text="计划设置", bg=BG, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(parent, text="只填两个数：每天花多久、什么时候考。",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", padx=16, pady=(0, 14))

        row1 = tk.Frame(parent, bg=BG)
        row1.pack(fill="x", padx=16)
        tk.Label(row1, text="每天", bg=BG, fg=DIM, font=(FONT, 9), width=5,
                 anchor="w").pack(side="left")
        mpd_var = tk.StringVar(value=str(MINUTES_PER_DAY))
        tk.Entry(row1, textvariable=mpd_var, bg=CARD, fg=FG, insertbackground=FG,
                 bd=0, font=(FONT, 9), highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=ACCENT, width=6).pack(side="left", ipady=4)
        tk.Label(row1, text="分钟", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(6, 0))

        row2 = tk.Frame(parent, bg=BG)
        row2.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(row2, text="目标日", bg=BG, fg=DIM, font=(FONT, 9), width=5,
                 anchor="w").pack(side="left")
        dl_var = tk.StringVar(value=PLAN_DEADLINE or "")
        tk.Entry(row2, textvariable=dl_var, bg=CARD, fg=FG, insertbackground=FG,
                 bd=0, font=(FONT, 9), highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=ACCENT, width=14).pack(side="left", ipady=4)
        tk.Label(row2, text="如 2027-05-22", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(8, 0))

        tip = tk.Label(parent, text="", bg=BG, fg=DIM, font=(FONT, 8),
                       wraplength=420, justify="left", anchor="w")
        tip.pack(anchor="w", padx=16, pady=(16, 0))

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
                tip.config(text=f"没设目标日。剩 {remain/60:.0f} 小时，"
                                f"按每天 {mpd} 分钟约 {-(-int(remain)//mpd)} 天完成。", fg=MUTED)
                return
            deadline = datetime.strptime(dl, "%Y-%m-%d").date()
            total = (deadline - today_d).days + 1
            if total <= 0:
                tip.config(text="目标日已经过去了。", fg="#E57373")
                return
            need = remain / total
            ok = "✓ 来得及" if need <= mpd else "⚠ 不够"
            tip.config(text=f"剩 {total} 天，还剩 {remain/60:.0f} 小时。\n"
                            f"需要 {need:.0f} 分钟/天，你设的是 {mpd} 分钟。{ok}",
                       fg=OK if need <= mpd else "#E57373")

        mpd_var.trace_add("write", lambda *_: preview())
        dl_var.trace_add("write", lambda *_: preview())
        preview()

        status = tk.Label(parent, text="", bg=BG, fg=MUTED, font=(FONT, 8), anchor="w")
        status.pack(fill="x", padx=16, pady=(10, 0))

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=16, pady=12)

        def save():
            mpd, dl, err = read_vals()
            if err:
                status.config(text=err, fg="#E57373")
                return
            MINUTES_PER_DAY, PLAN_DEADLINE = mpd, dl
            self._write_plan()
            self._close_panel()
            self._refresh()

        tk.Button(row, text="保存", command=save, bg=CARD, fg=OK, bd=1, relief="flat",
                  highlightbackground=LINE, activebackground=OK, activeforeground="#111",
                  font=(FONT, 9, "bold"), cursor="hand2", width=9).pack(side="left")
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
            text=f"已投入 {spent:.1f}h / 预算 {hours:g}h · {cnt} 次记录 · 点这里查看" if cnt
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
