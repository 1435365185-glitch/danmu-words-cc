# -*- coding: utf-8 -*-
"""
弹幕背单词 - 桌面全局悬浮版 v3
- 鼠标悬停任意单词：所有弹幕停住，其他单词变半透明
- 左键点击：英文发音（离线，Windows自带语音）+ 下方例句气泡
- 中键：标记已掌握
- 右键：菜单
"""
import sys
import os
import json
import random
import subprocess
import ctypes
import ctypes.wintypes
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon,
    QGraphicsOpacityEffect, QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont, QAction, QIcon, QPixmap, QColor, QPainter, QActionGroup

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.json")

COLORS = [
    "#2E7D32", "#C0652A", "#7B4FAE", "#C94C4C",
    "#2E8B8B", "#5B6ABF", "#B04A8A",
]

SPEED = 1.8
SPAWN_INTERVAL = 4000
MOVE_INTERVAL = 30
EXAMPLE_DURATION = 6000
DIM_OPACITY = 0.15  # 悬停时其他单词的透明度（越低越透）
BASE_OPACITY = 0.85  # 平时单词标签的基础透明度


def load_words():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("words", [])
    return []


def save_words(words):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"words": words}, f, ensure_ascii=False, indent=2)


class ExampleBubble(QWidget):
    def __init__(self, parent, example_en, example_cn):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 235);
                border-radius: 10px;
                padding: 8px 12px;
            }
            QLabel#en { color: #FFD966; font-size: 12px; font-weight: bold; }
            QLabel#cn { color: #EEEEEE; font-size: 12px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        lb_en = QLabel(example_en)
        lb_en.setObjectName("en")
        lb_en.setWordWrap(True)
        lb_cn = QLabel(example_cn)
        lb_cn.setObjectName("cn")
        lb_cn.setWordWrap(True)
        layout.addWidget(lb_en)
        layout.addWidget(lb_cn)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.adjustSize()


class WordLabel(QLabel):
    def __init__(self, word_data, pos, color, host):
        super().__init__(word_data["word"], host)
        self.host = host
        self.data = word_data
        self.hovering = False
        self.bubble = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(BASE_OPACITY)
        self.setGraphicsEffect(self._opacity_effect)

        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self._base_style = f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 12px;
                padding: 6px 18px;
            }}
        """
        self.setStyleSheet(self._base_style)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_Hover, True)
        self.adjustSize()
        self._normal_width = self.width()  # 记录只有英文时的宽度
        self.move(pos)

    def enterEvent(self, e):
        # 游戏模式下不响应悬停，保持纯展示
        if self.host.game_mode:
            return
        self.hovering = True
        meaning = self.data.get("meaning", "")
        pos = self.data.get("pos", "")
        if meaning:
            # 向下展开：上面英文，下面中文，宽度固定
            self.setFixedWidth(self._normal_width)
            self.setTextFormat(Qt.RichText)
            self.setText(
                f"<div style='text-align:center;line-height:1.3;'>"
                f"<b>{self.data['word']}</b><br>"
                f"<span style='font-weight:normal;font-size:10px;'>{pos}{meaning}</span>"
                f"</div>"
            )
            self.setWordWrap(True)
            self.adjustSize()
        self.host.on_hover_start(self)

    def leaveEvent(self, e):
        self.hovering = False
        if not self.data.get("known"):
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setTextFormat(Qt.PlainText)
            self.setText(self.data["word"])
            self.setWordWrap(False)
            self.adjustSize()
        self.host.on_hover_end(self)

    def mousePressEvent(self, e):
        # 游戏模式下完全穿透，点击不触发任何操作
        if self.host.game_mode:
            return
        if e.button() == Qt.LeftButton:
            self.speak()
            self.show_bubble()
        elif e.button() == Qt.MiddleButton:
            self.mark_known()
        elif e.button() == Qt.RightButton:
            self.host.show_label_menu(self, e.globalPos())

    def speak(self):
        word = self.data["word"]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Speech;"
                 "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                 "$s.SelectVoice('Microsoft Zira Desktop');"
                 f"$s.Speak('{word}')"],
                startupinfo=startupinfo
            )
        except Exception:
            pass

    def set_dimmed(self, dimmed):
        """设置半透明/恢复"""
        self._opacity_effect.setOpacity(DIM_OPACITY if dimmed else BASE_OPACITY)

    def show_bubble(self):
        if self.bubble:
            self.bubble.deleteLater()
            self.bubble = None
        en = self.data.get("example", "")
        cn = self.data.get("example_cn", "")
        if not en and not cn:
            return
        self.bubble = ExampleBubble(self.parentWidget(), en, cn)
        bx = self.x() + (self.width() - self.bubble.width()) // 2
        by = self.y() + self.height() + 6
        self.bubble.move(bx, by)
        self.bubble.show()
        QTimer.singleShot(EXAMPLE_DURATION, self._hide_bubble)

    def _hide_bubble(self):
        if self.bubble:
            self.bubble.deleteLater()
            self.bubble = None

    def mark_known(self):
        self.data["known"] = True
        self.host.save_known(self.data["word"])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #9E9E9E;
                color: #DDDDDD;
                border-radius: 12px;
                padding: 6px 18px;
            }}
        """)
        if not self.hovering:
            self.setText(self.data["word"])
            self.adjustSize()


class DanmuWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.words = load_words()
        self.labels = []
        self.paused = False
        self.game_mode = False          # 游戏模式（单词点击穿透）
        self._hover_label = None  # 当前悬停的标签
        self._init_ui()
        self._init_tray()

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._tick)
        self.move_timer.start(MOVE_INTERVAL)

        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self._spawn)
        self.spawn_timer.start(SPAWN_INTERVAL)

    def _init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def _init_tray(self):
        pix = QPixmap(32, 32)
        pix.fill(QColor("#7B4FAE"))
        p = QPainter(pix)
        p.setPen(QColor("white"))
        p.setFont(QFont("Arial", 12, QFont.Bold))
        p.drawText(pix.rect(), Qt.AlignCenter, "W")
        p.end()
        self.tray = QSystemTrayIcon(QIcon(pix), self)
        self.tray.setToolTip("弹幕背单词")
        menu = QMenu()
        self.act_pause = QAction("暂停弹幕", self)
        self.act_pause.triggered.connect(self.toggle_pause)

        # 两种点击模式（互斥单选）
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.act_smart = QAction("智能模式：游戏时自动点不到", self, checkable=True)
        self.act_always = QAction("始终可点", self, checkable=True)
        self.mode_group.addAction(self.act_smart)
        self.mode_group.addAction(self.act_always)
        self.act_smart.triggered.connect(lambda: self.set_smart_mode(True))
        self.act_always.triggered.connect(lambda: self.set_smart_mode(False))
        self.act_smart.setChecked(True)
        self.smart_mode = True

        act_reset = QAction("重置已掌握", self)
        act_reset.triggered.connect(self.reset_known)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(self.act_pause)
        menu.addSeparator()
        menu.addAction(self.act_smart)
        menu.addAction(self.act_always)
        menu.addSeparator()
        menu.addAction(act_reset)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        # 智能模式：每秒检测前台窗口是否全屏（游戏/全屏视频）
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_fullscreen)
        self.check_timer.start(1000)

    def set_smart_mode(self, smart):
        """选择点击模式：True=智能（游戏时自动点不到），False=始终可点"""
        self.smart_mode = smart
        if not smart:
            self.set_game_mode(False)
        self.tray.showMessage("弹幕背单词",
                              "智能模式：游戏时自动点不到" if smart else "始终可点",
                              QSystemTrayIcon.Information, 1200)

    def _check_fullscreen(self):
        """智能模式下：前台窗口占满屏幕（游戏/全屏视频）→ 点不到；否则可点"""
        if not self.smart_mode:
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            screen = QApplication.primaryScreen().geometry()
            is_fullscreen = (w >= screen.width() * 0.95 and
                             h >= screen.height() * 0.95)
            self.set_game_mode(is_fullscreen)
        except Exception:
            pass

    # ---- 游戏模式 ----
    def _set_click_through(self, on):
        """Windows底层真穿透：窗口照常显示，但鼠标点击直接穿过"""
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
            user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
            user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            if on:
                ex |= WS_EX_TRANSPARENT
            else:
                ex &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
            # 刷新窗口样式使其立即生效
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                0x0001 | 0x0002 | 0x0020)  # SWP_NOSIZE|SWP_NOMOVE|SWP_FRAMECHANGED
        except Exception:
            pass

    def set_game_mode(self, on):
        """切换：on=True=单词点不到（穿透），on=False=单词可点"""
        if on == self.game_mode:
            return
        self.game_mode = on
        if on:
            # 开启穿透：清掉悬停展开状态，恢复纯英文
            for lb in self.labels:
                lb._hide_bubble()
            self._hover_label = None
            for lb in self.labels:
                lb.hovering = False
                lb.setMinimumWidth(0)
                lb.setMaximumWidth(16777215)
                lb.setTextFormat(Qt.PlainText)
                lb.setText(lb.data["word"])
                lb.setWordWrap(False)
                lb.adjustSize()
                lb.set_dimmed(False)
            self._set_click_through(True)
        else:
            # 恢复可点击：移除穿透
            self._set_click_through(False)

    def on_hover_start(self, label):
        """某个标签被悬停：所有标签停住，其他变半透明"""
        self._hover_label = label
        for lb in self.labels:
            lb.set_dimmed(lb is not label)

    def on_hover_end(self, label):
        """某个标签离开：如果离开的是当前悬停的标签，恢复全部"""
        if self._hover_label is label:
            self._hover_label = None
            for lb in self.labels:
                lb.set_dimmed(False)

    def _spawn(self):
        if self.paused:
            return
        # 检查右边是否有单词靠近边缘，有就等下一轮，避免重合
        if any(lb.x() > self.width() - 200 for lb in self.labels):
            return
        pool = [w for w in self.words if not w.get("known")]
        if not pool:
            return
        word = random.choice(pool)
        color = random.choice(COLORS)
        y = 25
        label = WordLabel(word, QPoint(self.width() + 20, y), color, self)
        label.show()
        self.labels.append(label)

    def _tick(self):
        # 悬停模式下全部停住
        if self._hover_label is not None:
            return
        for lb in self.labels[:]:
            nx = lb.x() - SPEED
            if nx < -lb.width() - 10:
                lb._hide_bubble()
                lb.deleteLater()
                self.labels.remove(lb)
            else:
                lb.move(nx, lb.y())
                if lb.bubble:
                    bx = lb.x() + (lb.width() - lb.bubble.width()) // 2
                    by = lb.y() + lb.height() + 6
                    lb.bubble.move(bx, by)

    def show_label_menu(self, label, global_pos):
        m = QMenu()
        a_speak = QAction("播放发音", self)
        a_speak.triggered.connect(lambda: (label.speak(), label.show_bubble()))
        a_known = QAction("标记已掌握", self)
        a_known.triggered.connect(label.mark_known)
        m.addAction(a_speak)
        m.addAction(a_known)
        m.exec(global_pos)

    def save_known(self, word):
        for w in self.words:
            if w["word"] == word:
                w["known"] = True
                break
        save_words(self.words)

    def toggle_pause(self):
        self.paused = not self.paused
        self.act_pause.setText("继续播放" if self.paused else "暂停弹幕")
        self.tray.showMessage("弹幕背单词",
                              "已暂停" if self.paused else "继续播放",
                              QSystemTrayIcon.Information, 1200)

    def reset_known(self):
        for w in self.words:
            w["known"] = False
        save_words(self.words)
        self.tray.showMessage("弹幕背单词", "已重置已掌握列表",
                             QSystemTrayIcon.Information, 1200)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = DanmuWindow()
    win.show()
    sys.exit(app.exec())
