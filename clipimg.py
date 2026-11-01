#!/usr/bin/env python3
"""从 Windows 剪贴板取图，纯标准库。

Windows 截图工具（Win+Shift+S / PrtSc）往剪贴板放的是 CF_DIB 原始位图，
不是 PNG。所以流程是：读 DIB -> 转 PPM -> Tk 读入 -> 写出 PNG -> base64。
中间不落任何永久文件。
"""

import ctypes
import os
import sys
import tempfile
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"

CF_DIB = 8
CF_DIBV5 = 17
CF_HDROP = 15

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
else:
    user32 = None      # 非 Windows：粘贴图片不可用，功能降级为「＋ 添加」选文件


def _read_clipboard_bytes(fmt):
    """按格式取剪贴板原始字节。GlobalLock 后按 HGLOBAL 大小拷贝。"""
    handle = user32.GetClipboardData(fmt)
    if not handle:
        return None
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

    size = kernel32.GlobalSize(handle)
    ptr = kernel32.GlobalLock(handle)
    if not ptr or not size:
        return None
    try:
        return ctypes.string_at(ptr, size)
    finally:
        kernel32.GlobalUnlock(handle)


def _parse_dib(data):
    """DIB -> (width, height, rgb_bytes)。只支持 BI_RGB 的 24/32 位，够覆盖截图工具。"""
    if len(data) < 40:
        raise ValueError("DIB 数据太短")
    header_size = int.from_bytes(data[0:4], "little")
    width = int.from_bytes(data[4:8], "little", signed=True)
    height = int.from_bytes(data[8:12], "little", signed=True)
    bit_count = int.from_bytes(data[14:16], "little")
    compression = int.from_bytes(data[16:20], "little")

    if compression not in (0, 3):
        raise ValueError(f"不支持的位图压缩格式 {compression}（只认 BI_RGB/BI_BITFIELDS）")
    if bit_count not in (24, 32):
        raise ValueError(f"不支持的位深 {bit_count}，只认 24/32 位")

    top_down = height < 0
    width, height = abs(width), abs(height)

    # 调色板 / 掩码：24 位以下有调色板，32 位 BI_BITFIELDS 头后带 3 个掩码
    offset = header_size
    if compression == 3 and bit_count == 32:
        offset += 12

    stride = ((bit_count * width + 31) // 32) * 4
    need = offset + stride * height
    if len(data) < need:
        raise ValueError("DIB 数据长度不足，可能被截断")

    out = bytearray(width * height * 3)
    step = bit_count // 8
    for row in range(height):
        src_y = row if top_down else (height - 1 - row)
        base = offset + src_y * stride
        dst = row * width * 3
        for x in range(width):
            p = base + x * step
            out[dst + x * 3] = data[p + 2]      # R
            out[dst + x * 3 + 1] = data[p + 1]  # G
            out[dst + x * 3 + 2] = data[p]      # B
    return width, height, bytes(out)


def _dib_to_png(root, dib):
    """DIB -> PNG 字节。借 Tk 的 PPM 读入 + PNG 写出，避开第三方图像库。"""
    import tkinter as tk
    width, height, rgb = _parse_dib(dib)
    with tempfile.TemporaryDirectory() as tmp:
        ppm_path = os.path.join(tmp, "d.ppm")
        with open(ppm_path, "wb") as f:
            f.write(b"P6\n%d %d\n255\n" % (width, height))
            f.write(rgb)
        img = tk.PhotoImage(master=root, file=ppm_path)
        png_path = os.path.join(tmp, "d.png")
        img.write(png_path, format="png")
        with open(png_path, "rb") as f:
            return f.read()


def grab_image(root):
    """读剪贴板图片。成功返回 {"b64","mime","name","width","height"}，没有图返回 None。"""
    import base64
    if not IS_WINDOWS:
        return None
    if not user32.IsClipboardFormatAvailable(CF_DIB) and \
       not user32.IsClipboardFormatAvailable(CF_DIBV5):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        data = _read_clipboard_bytes(CF_DIBV5) or _read_clipboard_bytes(CF_DIB)
    finally:
        user32.CloseClipboard()
    if not data:
        return None
    png = _dib_to_png(root, data)
    return {"b64": base64.b64encode(png).decode("ascii"), "mime": "image/png",
            "name": "剪贴板图片.png", "bytes": len(png)}


def clipboard_files():
    """剪贴板里如果是文件（资源管理器复制），返回路径列表。"""
    if not IS_WINDOWS:
        return []
    if not user32.IsClipboardFormatAvailable(CF_HDROP):
        return []
    if not user32.OpenClipboard(None):
        return []
    try:
        handle = user32.GetClipboardData(CF_HDROP)
        if not handle:
            return []
        shell32 = ctypes.windll.shell32
        shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT,
                                           wintypes.LPWSTR, wintypes.UINT]
        count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
        paths = []
        for i in range(count):
            buf = ctypes.create_unicode_buffer(1024)
            shell32.DragQueryFileW(handle, i, buf, 1024)
            if buf.value:
                paths.append(buf.value)
        return paths
    finally:
        user32.CloseClipboard()
