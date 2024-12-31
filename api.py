import ctypes
from ctypes.wintypes import *

__all__ = ["GetFgWindow", "GetWindowText", "GetProcessInfo", "GetWindowHandle", "SendClose", "ForceClose"]

User32 = ctypes.windll.user32
Kernel32 = ctypes.windll.kernel32

# 定义ULONG_PTR
if ctypes.sizeof(ctypes.c_void_p) == 4:  # 32位系统
    ULONG_PTR = ctypes.c_ulong
else:  # 64位系统
    ULONG_PTR = ctypes.c_ulonglong


# 获取前台窗口句柄
class GetFgWindow:
    def __init__(self):
        """
        获取前台窗口句柄
        """
        self.GetFgWindow = User32.GetForegroundWindow
        self.GetFgWindow.restype = ctypes.c_void_p

    def __call__(self) -> int | None:
        return self.GetFgWindow()


# 获取窗口名称
class GetWindowText:
    def __init__(self):
        """
        获取窗口名称
        """
        self.GetFgWindow = User32.GetForegroundWindow
        self.GetFgWindow.restype = ctypes.c_void_p
        self.GetWindowText = User32.GetWindowTextW
        self.GetWindowText.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int)
        self.GetWindowText.restype = ctypes.c_int
        self.buffer = ctypes.create_unicode_buffer(256)

    # 调用时返回窗口名称
    def __call__(self, hwnd: int | None = None) -> str:
        """
        获取窗口名称
        :param hwnd: 指定窗口句柄，默认为None，表示获取当前前台窗口的名称
        :return:     窗口名称
        """
        if hwnd: self.GetWindowText(hwnd, self.buffer, 256)  # 指定窗口句柄
        else: self.GetWindowText(self.GetFgWindow(), self.buffer, 256)  # 获取当前前台窗口的名称
        return self.buffer.value


# 用于获取进程信息
class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),  # 结构体大小
        ("cntUsage", DWORD),  # 引用计数
        ("th32ProcessID", DWORD),  # 进程ID (PID)
        ("th32DefaultHeapID", ULONG_PTR),  # 默认堆ID
        ("th32ModuleID", DWORD),  # 模块ID
        ("cntThreads", DWORD),  # 线程数
        ("th32ParentProcessID", DWORD),  # 父进程ID
        ("pcPriClassBase", LONG),  # 优先级
        ("dwFlags", DWORD),  # 标志
        ("szExeFile", ctypes.c_char * 260),  # 进程名称
    ]


# 获取进程信息
class GetProcessInfo:
    def __init__(self):
        """
        获取 “进程ID（pid）： 进程名称（exe）” 字典
        """
        # 创建快照
        self.CreateSnapshot = Kernel32.CreateToolhelp32Snapshot
        self.CreateSnapshot.argtypes = [DWORD, DWORD]
        self.CreateSnapshot.restype = HANDLE
        # 关闭快照
        self.CloseHandle = Kernel32.CloseHandle
        self.CloseHandle.argtypes = [HANDLE]
        self.CloseHandle.restype = BOOL
        # 枚举进程
        self.Process32First = Kernel32.Process32First
        self.Process32First.argtypes = [HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        self.Process32First.restype = BOOL
        # 枚举下一个进程
        self.Process32Next = Kernel32.Process32Next
        self.Process32Next.argtypes = [HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        self.Process32Next.restype = BOOL

    # 获取pid: name字典
    def __call__(self, sort: bool = False) -> dict:
        """
        获取pid: name字典
        :param sort: 是否按pid排序
        :return: pid: name字典 | {}
        """
        # 创建快照
        h_snapshot = self.CreateSnapshot(0x00000002, 0)
        if h_snapshot == -1:  # 创建快照失败
            return {}
        session = PROCESSENTRY32()
        session.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if not self.Process32First(h_snapshot, ctypes.byref(session)):  # 枚举第一个进程失败
            self.CloseHandle(h_snapshot)
            return {}

        process_dict = {}
        while True:
            process_dict[session.th32ProcessID] = session.szExeFile.decode("mbcs")  # 进程ID:进程名称
            if not self.Process32Next(h_snapshot, ctypes.byref(session)):  # 枚举下一个进程失败
                break

        self.CloseHandle(h_snapshot)  # 关闭快照
        if sort:  # 按pid排序
            return dict(sorted(process_dict.items(), key=lambda x: x[0]))  # 根据pid排序
        return process_dict


# 获取所有顶层窗口句柄及相关信息
class GetWindowHandle:
    def __init__(self):
        """
        获取 ”窗口句柄：(pid, 窗口标题)“ 字典
        """
        self.ProcessData: dict[int, tuple[int, str]] = {}  # {hwnd: (pid, title), ...}
        # 定义回调函数
        self.EnumWindows = User32.EnumWindows
        self.EnumWindows.argtypes = [HWND, LPARAM]
        self.EnumWindows.restype = BOOL
        # 定义获取进程ID的函数
        self.GetProcessId = User32.GetWindowThreadProcessId
        self.GetProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
        self.GetProcessId.restype = DWORD
        # 定义获取窗口标题长度的函数
        self.GetLengthW = User32.GetWindowTextLengthW
        self.GetLengthW.argtypes = [HWND]
        self.GetLengthW.restype = ctypes.c_int
        # 定义获取窗口标题的函数
        self.GetWindowTextW = User32.GetWindowTextW
        self.GetWindowTextW.argtypes = [HWND, ctypes.c_wchar_p, ctypes.c_int]
        self.GetWindowTextW.restype = ctypes.c_int

    def __call__(self, sort: bool = False) -> dict:
        """
        枚举所有顶层窗口
        :param sort: 是否按窗口句柄排序
        :return:  hwnd: (pid, title)字典
        """
        func = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)(self._callback)
        self.EnumWindows(func, 0)
        if sort:  # 按窗口句柄排序
            return dict(sorted(self.ProcessData.items(), key=lambda x: x[0]))   # 根据hwnd排序
        return self.ProcessData

    def _callback(self, hwnd, lParam):
        _ = lParam
        PID = DWORD()
        self.GetProcessId(hwnd, ctypes.byref(PID))
        length = self.GetLengthW(hwnd)
        BUFF = ctypes.create_unicode_buffer(length + 1)
        self.GetWindowTextW(hwnd, BUFF, length + 1)
        if BUFF.value:  # 窗口标题不为空
            self.ProcessData[hwnd] = (PID.value, BUFF.value)  # 添加到字典中
        return True


# 关闭窗口
class SendClose:
    def __init__(self):
        self.SendMessage = User32.SendMessageW
        self.SendMessage.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p)
        self.SendMessage.restype = ctypes.c_long

    def __call__(self, hwnd: int) -> int:
        return self.SendMessage(hwnd, 0x10, 0, 0)


# 强制关闭应用
class ForceClose:
    def __init__(self):
        # 打开进程
        self.OpenProcess = Kernel32.OpenProcess
        self.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_long, ctypes.c_ulong)
        self.OpenProcess.restype = ctypes.c_void_p
        # 关闭进程
        self.TerminateProcess = Kernel32.TerminateProcess
        self.TerminateProcess.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        self.TerminateProcess.restype = ctypes.c_long

    def __call__(self, pid: int) -> bool:
        hProcess = self.OpenProcess(0x0001, False, pid)  # 打开进程, 0x0001: PROCESS_TERMINATE
        if not hProcess: return False
        result = self.TerminateProcess(hProcess, 1)
        Kernel32.CloseHandle(hProcess)  # 关闭进程句柄
        if result: return True
        return False
