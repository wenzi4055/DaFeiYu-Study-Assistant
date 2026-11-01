import ctypes, json, pathlib, io, sys
ctypes.windll.shcore.SetProcessDpiAwareness(2)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import tkinter as tk, PIL.ImageGrab, dafeiyu
sf = pathlib.Path("dafeiyu_state.json"); sf.unlink(missing_ok=True)
tf = pathlib.Path("tasks.json"); tf.unlink(missing_ok=True)
dafeiyu.load_config()
dafeiyu.PLAN_DEADLINE = "2027-05-22"
root = tk.Tk(); app = dafeiyu.DaFeiYu(root); app._refresh(); app._select("ds1")
def grab(n):
    root.update()
    x,y,w,h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    PIL.ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(n)
def step():
    print("今日行:", app.today_label.cget("text"))
    print("差距行:", app.gap_label.cget("text"))
    grab("_p1.png")
    app._open_plan(); grab("_p2.png"); app._close_panel()
    root.destroy()
root.after(900, step); root.mainloop()
