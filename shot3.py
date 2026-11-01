import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
import json, pathlib
sf = pathlib.Path("dafeiyu_state.json")
sf.write_text(json.dumps({"tasks": {"ds1": {"state": "done", "ts": "x"}, "ds2": {"state": "doing", "ts": "x"}}}, ensure_ascii=False), encoding="utf-8")
import tkinter as tk, PIL.ImageGrab, dafeiyu
dafeiyu.load_config()
root = tk.Tk(); app = dafeiyu.DaFeiYu(root); app._refresh()
def shot():
    root.update(); root.lift(); app._draw_bar()
    x,y,w,h = root.winfo_x(), root.winfo_y(), root.winfo_width(), root.winfo_height()
    PIL.ImageGrab.grab(bbox=(x,y,x+w,y+h)).save("docs/preview.png")
    print("left:", app.left_label.cget("text"), "| sub:", app.sub_label.cget("text"), "| detail:", app.detail_title.cget("text"))
    root.destroy()
root.after(1200, shot); root.mainloop()
