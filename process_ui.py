from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QGridLayout, QWidget
from PyQt6.QtWidgets import QPushButton, QLabel, QLineEdit
from PyQt6.QtGui import QIcon, QMouseEvent
# 没使用该模块，但必须得导入，所以下面的注释是用于屏蔽pycharm的警告
# noinspection PyUnresolvedReferences
import resources

__all__ = ["QApplication", "MainWindow"]


# 主窗口
class MainWindow(QMainWindow):
    def __init__(self, title="InkWn", size=(200, 90), positon=(0, 0), password: str = "123456", exit_func=None):
        """
        :param title:    窗口标题
        :param size:     窗口大小
        :param positon:  窗口位置
        :param password: 密码
        """
        super().__init__()
        # 初始化
        self.setWindowTitle(title)
        self.setGeometry(*positon, *size)
        self.setWindowIcon(QIcon(":/Icon.ico"))  # 设置图标，:表示资源路径，也就是resources.py
        self.setMaximumSize(size[0], size[1])
        self.setMinimumSize(size[0], size[1])
        # 常量
        self.password = password
        # 变量
        self.password_correctness = False  # 密码正确标志
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)   # 无边框，始终置顶
        # 绑定窗口关闭事件
        if exit_func is not None:
            self.closeEvent = exit_func
        # 布局
        self.widget = QWidget(self)
        self.layout = QGridLayout(self.widget)
        self.setCentralWidget(self.widget)  # 设置主窗口中心部件
        # 创建系统托盘
        self.tray = QSystemTrayIcon(QIcon(":/Icon.ico"), self)
        # noinspection PyUnresolvedReferences
        self.tray.activated.connect(lambda: self.show() if self.isHidden() else self.hide())  # 托盘点击事件
        self.tray.setVisible(True)  # 显示托盘图标
        # 控件
        self.edit = QLineEdit(self)  # 输入框
        self.move_label = QLabel("move", self)  # 拖动标签
        self.wait_timer = QTimer(self)  # 等待计时器
        # 变量
        self.wait_time: int = 2      # 输入错误等待时间，单位：秒
        self.timer_waitting_time: int = 0  # 计时器内部变量
        self.dragging = False        # 拖动标志
        self.drag_pos = QPoint()     # 拖动起始位置
        # 调用函数
        self._build_ui()
        self._build_move_label()

    # 规则
    def rules(self, text: str) -> bool:
        """
        规则，可重构
        :param text:  输入的文本
        :return:      规则是否通过
        """
        if text == self.password:
            return True
        # elif text == self.password + "-control":
        #     return True
        return False

    # 处理输入框信息
    def _obtain_input(self):
        if self.edit.isReadOnly():   # 输入框只读时不处理
            return
        input_text = self.edit.text()
        result = self.rules(input_text)
        if result:  # 规则返回True
            self.password_correctness = True
            self.close()
        else:       # 规则返回False
            self.edit.clear()   # 清空输入框
            self.edit.setReadOnly(True)  # 禁止输入
            self.edit.setPlaceholderText(f"无效指令，等待{self.wait_time}秒后重新输入")
            self.timer_waitting_time = self.wait_time
            self.wait_timer.start()   # 启动等待计时器
            if self.wait_time < 60:
                self.wait_time *= 2  # 等待时间翻倍

    # 构建UI
    # noinspection PyUnresolvedReferences
    def _build_ui(self):
        def timer():
            if self.timer_waitting_time > 1:
                self.timer_waitting_time -= 1
                self.edit.setPlaceholderText(f"无效指令，等待{self.timer_waitting_time}秒后重新输入")
            else:
                self.edit.setReadOnly(False)
                self.edit.setPlaceholderText("输入指令：")
                self.wait_timer.stop()

        # 输入框
        self.edit.setPlaceholderText("输入指令：")   # 设置提示文字
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)  # 密码模式
        self.edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单
        self.layout.addWidget(self.edit, 0, 0, 1, 3)
        # 计时器
        self.wait_timer.timeout.connect(timer)  # 计时器信号
        self.wait_timer.setInterval(1000)       # 计时器间隔，1秒
        self.wait_timer.setSingleShot(False)    # 循环计时器
        # 按钮
        enter_button = QPushButton("确定", self)
        self.layout.addWidget(enter_button, 1, 0, 1, 1)
        self.layout.addWidget(self.move_label, 1, 1, 1, 1)
        hide_button = QPushButton("隐藏", self)
        self.layout.addWidget(hide_button, 1, 2, 1, 1)
        # 信号与槽
        self.edit.returnPressed.connect(self._obtain_input)
        enter_button.clicked.connect(self._obtain_input)
        hide_button.clicked.connect(self.hide)

    # 构建拖动标签
    def _build_move_label(self):
        def press(event: QMouseEvent):
            # 鼠标按下事件处理
            if event.button() == Qt.MouseButton.LeftButton:  # 如果按下的是左键
                self.dragging = True  # 设置拖动状态为True
                self.drag_pos = event.pos()
                event.accept()  # 接受事件

        def move(event: QMouseEvent):
            # 鼠标移动事件处理
            if self.dragging:  # 如果处于拖动状态
                self.move(self.frameGeometry().topLeft() + event.pos() - self.drag_pos)  # 移动窗口
                event.accept()  # 接受事件

        def release(event: QMouseEvent):
            # 鼠标释放事件处理
            if event.button() == Qt.MouseButton.LeftButton:  # 如果释放的是左键
                self.dragging = False  # 设置拖动状态为False
                event.accept()  # 接受事件

        self.move_label.setMouseTracking(True)  # 开启鼠标跟踪
        self.move_label.setCursor(Qt.CursorShape.SizeAllCursor)  # 设置鼠标图标
        self.move_label.mousePressEvent = press
        self.move_label.mouseMoveEvent = move
        self.move_label.mouseReleaseEvent = release
