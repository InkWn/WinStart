import os
import sys
import time
from threading import Thread

from api import *
from process_ui import MainWindow, QApplication

# 是否为windows系统
if os.name != "nt":
    print("请在Windows系统上运行本程序！")
    sys.exit(0)

# item文件默认内容
ITEM_DEFAULT_DATA = """:enable(true)
:password(123456)
:record_all(true)
:interval(0.1)
:level(1)
;;

[Protect]{
(0)[System Process]
(0)System
(0)explorer.exe
(0)svchost.exe
(0)dwm.exe
}

[Ordinary]{
QQ
微信
}

[Force]{
}

[Include]{
}

[ExInclude]{
}

;;;;
"""

# 路径常量
ITEM_PATH = ...    # 待检测文件路径
RECORD_PATH = ...  # 日志文件的路径

# 全局变量
UiExit = False  # ui线程退出标志
PasswordCorrectness = False  # 密码正确标志


# 获取当前日期
def get_date() -> str:
    return time.strftime("%Y年%m月%d日", time.localtime(time.time()))


# 获取当前时间
def get_time() -> str:
    return time.strftime("%H:%M:%S", time.localtime(time.time()))


# 检测文件并修复
def check_file():
    global ITEM_PATH, RECORD_PATH
    path = os.path.dirname(sys.argv[0])   # 获取当前程序路径
    ITEM_PATH = path + "\\item"
    RECORD_PATH = path + "\\record.log"
    if not os.path.exists(RECORD_PATH):  # 日志文件不存在
        with open(RECORD_PATH, "w", encoding="utf-8") as f:
            f.write(f"{get_date()}\n\t[{get_time()}]: [Info]日志文件({RECORD_PATH})已创建;\n")
    else:  # 日志文件存在，写入日期
        with open(RECORD_PATH, "a", encoding="utf-8") as f:
            f.write(f"{get_date()}\n")
    if not os.path.exists(ITEM_PATH):  # item文件不存在
        with open(ITEM_PATH, "w", encoding="utf-8") as f:
            f.write(ITEM_DEFAULT_DATA)
        with open(RECORD_PATH, "a", encoding="utf-8") as f:
            f.write(f"\t[{get_time()}]: [Info]item文件({ITEM_PATH})已修复;\n")
    else:
        with open(RECORD_PATH, "a", encoding="utf-8") as f:
            f.write(f"\t[{get_time()}]: [Info]程序正常运行;\n")


# 获取配置信息
def get_config() -> tuple[dict, dict]:
    """
    :return: tuple[dict, dict] -> (配置信息, 规则信息)
    """
    config = {
        "enable": 'true',
        "password": '123456',
        "record_all": 'true',
        "interval": '0.1',
        "level": '1',
    }  # 默认配置信息
    rule = {
        "Protect": {0: [], 1: []},
        "Ordinary": [],
        "Force": [],
        "Include": [],
        "ExInclude": [],
    }  # 规则信息
    with open(ITEM_PATH, "r", encoding="utf-8") as f:
        text = f.readlines()
        text = [line.strip() for line in text if line.strip()]  # 去除所有\n与空字符串
    read_type = "config"  # 循环时读取类型，data或rule或protect或other
    rule_value = ""  # 记录当前rule类型键
    for line in text:
        if not line: continue  # 空行，跳过
        if line.startswith("#"): continue  # 注释行，跳过
        if read_type == "config":  # 读取配置信息
            if line == ";;": read_type = "rule"  # 配置信息分隔符
            if line.startswith(":"):  # ':'开头的是配置信息
                try: key, value = line.strip(":").split("(")  # 去除':'和'('
                except ValueError: continue  # 格式错误，跳过
                if key not in config: continue  # 未知配置信息，跳过
                config[key] = value.strip(")")  # 去除')'并赋值
        elif read_type == "rule":  # 读取规则信息
            if line == ";;;;": break  # 文本末尾，结束读取
            if line.startswith("["):  # [开头的行是规则信息
                if line == "[Protect]{":  # 进入Protect规则读取
                    read_type = "protect"  # 进入保护规则读取
                else:  # 非Protect规则
                    try: rule_value = line.strip("[]{").strip()  # 提取[]内的规则类型
                    except ValueError: continue  # 格式错误，跳过
                    read_type = "other"  # 进入除Protect外的规则读取
        elif read_type == "protect":  # 读取保护内容
            if line == "}":  # 到达规则内容结束符
                read_type = "rule"  # 回到规则信息读取
                continue
            if len(line) <= 3: continue  # 仅有'(0)'、'(1)'或太短
            if line.startswith("(0)"):  # (0)开头的行表示根据进程名检测
                rule["Protect"][0].append(line[3:])  # 加入规则内容
            elif line.startswith("(1)"):  # (1)开头的行表示根据窗口标题检测
                rule["Protect"][1].append(line[3:])  # 加入规则内容
        else:  # 读取除Protect外的规则内容
            if line == "}":  # 到达规则内容结束符
                read_type = "rule"  # 回到规则信息读取
                continue
            rule[rule_value].append(line)  # 加入规则内容
    return config, rule


# ui主程序
def ui_main(password: str):
    def exit_func(event):  # 退出函数，必须有参数event，该函数用于替换PyQt6的退出函数
        global PasswordCorrectness, UiExit
        PasswordCorrectness = window.password_correctness  # 获取密码正确标志
        UiExit = True  # 标记ui线程退出

    app = QApplication(sys.argv)
    window = MainWindow(password=password, exit_func=exit_func)
    window.show()
    sys.exit(app.exec())


# 监听窗口标题
def listen_text(config: dict, rule: dict):
    # 常量
    interval = 0.1  # 检测间隔，单位为秒
    level = 2  # 检测等级
    record_all = config["record_all"] == "true"  # 是否记录所有记录
    try:
        interval = float(config["interval"])
        if interval < 0.01: interval = 0.01  # 间隔不能小于0.01秒
    except ValueError: pass  # 无效的间隔
    try:
        level = int(config["level"])
        if not (1 <= level <= 3): level = 2  # 等级不能超过3或小于1
    except ValueError: pass  # 无效的等级
    # 变量
    last_text = ""  # 上一次检测的窗口标题
    last_froce = 0  # 上一个窗口是否是强制关闭目标
    # 调用api
    get_process_info = GetProcessInfo()
    get_window_handle = GetWindowHandle()
    get_fg_window = GetFgWindow()
    get_window_text = GetWindowText()
    send_close = SendClose()
    froce_close = ForceClose()
    # 获取保护进程pid
    protect_pids = [_pid for _pid, name in get_process_info().items() if name in rule["Protect"][0]]   # 保护进程pid列表
    # 高等级额外的功能
    if level >= 2:  # 加入任务管理器、cmd（有GUI界面）
        rule["Ordinary"].append("任务管理器")
        rule["Include"].append("cmd.exe")
    if level >= 3:  # 待拓展
        pass
    # 循环直到ui线程退出
    while not UiExit:
        hwnd = get_fg_window()  # 获取前台窗口hwnd
        window_text = get_window_text(hwnd)  # 获取窗口标题
        if not hwnd or not window_text:
            time.sleep(interval)
            continue  # 窗口无效，跳过
        if window_text == "InkWn":
            time.sleep(interval)
            continue  # 自己写的程序，跳过
        # 打开文件
        f = open(RECORD_PATH, "a", encoding="utf-8")
        if window_text == last_text:
            if hwnd == last_froce:  # 上一个窗口是强制关闭目标，则代表窗口关闭失败
                pid = get_window_handle()[hwnd][0]  # 获取窗口pid
                if pid in protect_pids:  # 窗口pid在保护进程pid中，可能是误判，跳过
                    f.write(f"\t[{get_time()}]: [Kill]窗口[{window_text}]关闭失败，该窗口可能为被保护程序;\n")
                    last_froce = 0  # 重置last_froce标志
                    time.sleep(interval)
                    continue
                if froce_close(pid):
                    f.write(f"\t[{get_time()}]: [Kill]正在尝试强制关闭[{window_text}]>>>关闭成功;\n")
                else:
                    f.write(f"\t[{get_time()}]: [Kill]正在尝试强制关闭[{window_text}]>>>关闭失败;\n")
                last_froce = 0  # 重置last_froce标志
            time.sleep(interval)
            continue  # 窗口标题未变化，跳过
        last_text = window_text  # 更新窗口标题
        last_froce = 0  # 重置last_froce标志
        # 判断窗口标题是否在保护规则(1)中
        if window_text in rule["Protect"][1]:
            f.write(f"\t[{get_time()}]: [Protect]访客正在访问保护程序[{window_text}];\n")
            time.sleep(interval)
            continue
        if window_text in rule["Ordinary"]:  # 窗口标题在普通规则中
            f.write(f"\t[{get_time()}]: [Ordinary]访客尝试打开[{window_text}]>>>已发送关闭窗口指令;\n")
            send_close(hwnd)  # 关闭窗口
            time.sleep(interval)
            continue
        elif window_text in rule["Force"]:  # 窗口标题在强制关闭规则中
            f.write(f"\t[{get_time()}]: [Force]访客尝试打开[{window_text}]>>>正在尝试关闭窗口;\n")
            send_close(hwnd)  # 尝试关闭窗口
            last_froce = hwnd  # 记录窗口为强制关闭目标
            time.sleep(interval)
            continue
        else:  # 检测包含类的窗口标题
            loop_signal = False  # for循环信号标志
            for include in rule["Include"]:
                if include in window_text:
                    f.write(f"\t[{get_time()}]: [Include]访客尝试打开[{window_text}]({include})>>>已发送关闭窗口指令;\n")
                    send_close(hwnd)  # 关闭窗口
                    loop_signal = True  #
                    time.sleep(interval)
                    break  # 结束for循环
            if loop_signal: continue  # 跳过本次while循环
            for exinclude in rule["ExInclude"]:
                if exinclude in window_text:
                    f.write(f"\t[{get_time()}]: [ExInclude]访客尝试打开[{window_text}]({exinclude})>>>正在尝试关闭窗口;\n")
                    send_close(hwnd)  # 关闭窗口
                    last_froce = hwnd  # 记录窗口为强制关闭目标
                    time.sleep(interval)
                    break  # 结束for循环
            if loop_signal: continue  # 跳过本次while循环
        # 记录所有窗口标题
        if record_all: f.write(f"\t[{get_time()}]: {window_text};\n")
        f.close()  # 关闭文件
        time.sleep(interval)


# 主程序
def main(config: dict, rule: dict):
    # 启动线程
    ui = Thread(target=ui_main, kwargs={"password": config["password"]}, daemon=True)
    ui.start()  # 启动ui线程
    Thread(target=listen_text, kwargs={"config": config, "rule": rule}).start()  # 启动监听窗口标题线程
    ui.join()  # 等待ui线程退出
    with open(RECORD_PATH, "a", encoding="utf-8") as f:
        if PasswordCorrectness:
            f.write(f"\t[{get_time()}]: [Exit]密码正确，已退出程序。\n")
        else:
            f.write(f"\t[{get_time()}]: [Exit]未知原因导致程序退出。\n")


if __name__ == '__main__':
    check_file()
    Config, Rule = get_config()
    if Config["enable"] != "true":  # 未启用，退出
        with open(RECORD_PATH, "a", encoding="utf-8") as file:
            file.write(f"\t[{get_time()}]: [Exit]程序未启用，已退出。\n")
        sys.exit(0)
    main(Config, Rule)  # 启动主程序
