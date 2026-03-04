import gradio as gr
from balance import BalanceController
import logging
import threading
import time
import os
import requests
# -------------------------------------------------
# 全局配置 & 日志系统（写入磁盘文件 ui.log）
# -------------------------------------------------
LOG_PATH = "ui.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ui")

def log(msg: str) -> None:
    """统一写入日志的函数，同时打印到控制台（方便调试）。"""
    logger.info(msg)
    for h in logger.handlers:
        h.flush()
    print(msg)  # optional, 可删除

controller: BalanceController | None = None   # 单例
motors_enabled = False   # 电机使能状态
port_opened: bool = False  # 是否已打开串口

# -------------------------------------------------
# 安全创建 BalanceController（带重试）
# -------------------------------------------------
def create_controller(retries: int = 3, delay: float = 1.0) -> BalanceController | None:
    """尝试实例化 BalanceController，失败则记录日志并返回 None。"""
    for attempt in range(1, retries + 1):
        try:
            log(f"尝试创建 BalanceController（第 {attempt} 次）")
            return BalanceController()
        except Exception as e:
            log(f"创建 BalanceController 失败: {e}")
            if attempt < retries:
                time.sleep(delay)
    log("全部重试结束，仍未能创建 BalanceController")
    return None

# ---------------------------------------
# ----------
# UI 操作函数（统一异常捕获、日志记录、返回状态文字）
# -------------------------------------------------
def open_port() -> tuple:
    """创建 BalanceController 实例并打开串口（不自动使能）。"""
    global controller, port_opened
    if controller is None:
        controller = create_controller()
        if controller is None:
            msg = "打开串口失败：无法创建 BalanceController"
            log(msg)
            port_opened = False
            return (msg, msg)
        msg = "串口已打开"
        log(msg)
        port_opened = True
        return (msg, msg)
    msg = "串口已打开（已存在实例）"
    log(msg)
    port_opened = True
    return (msg, msg)

def enable_all() -> tuple:
    """使能所有电机（腿部+轮子）。"""
    global motors_enabled
    if not port_opened:
        msg = "请先打开串口"
        log(msg)
        return (msg, msg)
    if controller is None:
        msg = "请先打开串口"
        return (msg, msg)
    try:
        controller.enable_all()
        motors_enabled = True
        msg = "电机已全部使能"
        log(msg)
        return (msg, msg)
    except Exception as e:
        msg = f"使能电机异常: {e}"
        log(msg)
        return (msg, msg)

def disable_all() -> tuple:
    """失能所有电机。"""
    global motors_enabled
    if not port_opened:
        msg = "请先打开串口"
        log(msg)
        return (msg, msg)
    if controller is None:
        msg = "请先打开串口"
        return (msg, msg)
    try:
        controller.disable_all()
        motors_enabled = False
        msg = "所有电机已失能"
        log(msg)
        return (msg, msg)
    except Exception as e:
        msg = f"失能电机异常: {e}"
        log(msg)
        return (msg, msg)

def set_position(pos1, pos2, pos3, pos4, vel) -> tuple:
    """设置四条腿的位置与速度比例。"""
    if not port_opened:
        msg = "请先打开串口"
        log(msg)
        return (msg, msg)
    if controller is None:
        msg = "请先打开串口"
        return (msg, msg)
    try:
        controller.control_legs_pos(pos1, pos2, pos3, pos4, vel)
        msg = f"已设置位置: {pos1}, {pos2}, {pos3}, {pos4}（速度比例 {vel}）"
        log(msg)
        return (msg, msg)
    except Exception as e:
        msg = f"设置位置异常: {e}"
        log(msg)
        return (msg, msg)

def get_torque() -> tuple:
    """读取四条腿的扭矩，返回字符串列表。"""
    if not port_opened:
        msg = "未打开串口"
        log(msg)
        return (["未打开串口"] * 4, msg)
    if controller is None:
        msg = "未打开串口"
        log(msg)
        return (["未打开串口"] * 4, msg)
    try:
        torques = controller.get_legs_torque()
        msg = f"读取扭矩: {torques}"
        log(msg)
        return ([f"{t:.2f}" if t is not None else "N/A" for t in torques], msg)
    except Exception as e:
        msg = f"读取扭矩异常: {e}"
        log(msg)
        return (["错误"] * 4, msg)

# -------------------------------------------------
# 后台平衡循环（守护线程）
# -------------------------------------------------
def _balance_thread(ctrl: BalanceController) -> None:
    """后台线程入口，运行平衡循环并确保资源安全释放。"""
    try:
        ctrl.enable_all()
        log("平衡循环启动")
        ctrl.run_balance_loop()
    except Exception as e:
        log(f"平衡循环异常: {e}")
    finally:
        ctrl.shutdown()
        log("平衡循环已结束，资源已清理")

def start_balance_thread() -> None:
    """在守护线程中启动平衡循环。"""
    global controller
    if controller is None:
        controller = create_controller()
        if controller is None:
            log("启动平衡控制失败：无法创建 BalanceController")
            return
    thread = threading.Thread(target=_balance_thread, args=(controller,), daemon=True)
    thread.start()
    log("平衡控制线程已启动")

def start_spd_thread(nomspd,offspd) -> None:
    """在守护线程中启动平衡循环。"""
    if controller is None:
        log("启动speed控制失败：无法创建 BalanceController")
        return
    controller.set_wheels_vel(nomspd,offspd)
    log("speed线程已启动")

def start_balance() -> tuple:
    """检查电机是否已使能后启动平衡控制。"""
    if not port_opened:
        msg = "请先打开串口"
        log(msg)
        return (msg, msg)
    if not motors_enabled:
        msg = "启动平衡控制失败：电机未使能"
        log(msg)
        return (msg, msg)
    start_balance_thread()
    msg = "平衡控制已启动"
    log(msg)
    return (msg, msg)

# -------------------------------------------------
# 日志刷新（用于 UI 按钮）
# -------------------------------------------------
def refresh_log() -> str:
    """读取最新的日志文件内容返回给 UI。"""
    if not os.path.exists(LOG_PATH):
        return ""
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------------------------------
# 自动打开串口并初始化 UI
# -------------------------------------------------
init_status = "未打开串口"

def control_speed(spd,off_spd):
    """检查电机是否已使能后启动平衡控制。"""
    if not port_opened:
        msg = "请先打开串口"
        log(msg)
        return (msg, msg)
    if not motors_enabled:
        msg = "启动平衡控制失败：电机未使能"
        log(msg)
        return (msg, msg)
    start_spd_thread(spd,off_spd)
    msg = "平衡控制已启动"
    log(msg)
    return (msg, msg)


def control_arms():
    url = "http://127.0.0.1:8081/action-group/run"
    try:
        response = requests.post(url, timeout=60)
        if response.status_code == 200:
            log("成功控制arms")
            return ("成功控制arms", "")
        else:
            log(f"控制arms失败: {response.text}")
            return (f"控制arms失败: {response.text}", "")
    except Exception as e:
        log(f"控制arms异常: {e}")
        return (f"控制arms异常: {e}", "")



# -------------------------------------------------
# Gradio UI
# -------------------------------------------------
with gr.Blocks() as demo:
    # 日志显示区
    log_box = gr.Textbox(label="运行日志", lines=15, interactive=False)
    refresh_btn = gr.Button("刷新日志")
    refresh_btn.click(fn=refresh_log, inputs=None, outputs=log_box)

    gr.Markdown("# 🤖 四足机器人控制面板")

    with gr.Row():
        # 左侧：电机控制
        with gr.Column():
            gr.Markdown("## 电机控制")
            # 已移除 “打开串口” 按钮，串口在启动时已自动打开
            open_btn    = gr.Button("🔌 打开串口")
            enable_btn  = gr.Button("✅ 使能全部")
            disable_btn = gr.Button("❌ 失能全部")
            start_btn   = gr.Button("▶️ 启动平衡控制")
            status_box  = gr.Textbox(label="状态", value=init_status, interactive=False)

            open_btn.click(fn=open_port, inputs=None, outputs=[status_box, log_box])
            enable_btn.click(fn=enable_all, inputs=None, outputs=[status_box, log_box])
            disable_btn.click(fn=disable_all, inputs=None, outputs=[status_box, log_box])
            start_btn.click(fn=start_balance, inputs=None, outputs=[status_box, log_box])
        
        with gr.Column():
            gr.Markdown("## 速度控制")
            normal_speed = gr.Slider(label="速度",minimum=-2,maximum=2,value=0.0,step=0.01)
            off_speed = gr.Slider(label="转向",minimum=-0.5,maximum=0.5,value=0.0,step=0.01)
            normal_speed.change(fn=control_speed,inputs=[normal_speed,off_speed], outputs=[status_box, log_box])
            off_speed.change(fn=control_speed,inputs=[normal_speed,off_speed], outputs=[status_box, log_box])
        # 右侧：扭矩读取
        with gr.Column():
            gr.Markdown("## 扭矩读取")
            torque_output = gr.Textbox(label="腿部扭矩 (N/m)", interactive=False)
            read_btn = gr.Button("读取扭矩")
            read_btn.click(fn=get_torque, inputs=None, outputs=[torque_output, log_box])

        # control arms
        with gr.Column():
            gr.Markdown("## arms")
            arm_btn = gr.Button("控制arms")
            arm_btn.click(fn=control_arms, inputs=None, outputs=[status_box, log_box])

    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)
