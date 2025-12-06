import gradio as gr
from balance import BalanceController
import logging
import threading
import time
import os

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

# -------------------------------------------------
# 全局状态
# -------------------------------------------------
controller: BalanceController | None = None   # 单例

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

# -------------------------------------------------
# UI 操作函数（统一异常捕获、日志记录、返回状态文字）
# -------------------------------------------------
def open_port() -> tuple:
    """创建 BalanceController 实例并打开串口（不自动使能）。"""
    global controller
    if controller is None:
        controller = create_controller()
        if controller is None:
            msg = "打开串口失败：无法创建 BalanceController"
            log(msg)
            return (msg, msg)
        msg = "串口已打开"
        log(msg)
        return (msg, msg)
    msg = "串口已打开（已存在实例）"
    log(msg)
    return (msg, msg)

def enable_all() -> tuple:
    """使能所有电机（腿部+轮子）。"""
    global motors_enabled
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

def start_balance() -> tuple:
    """检查电机是否已使能后启动平衡控制。"""
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
init_status, _ = open_port()  # 自动打开串口

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
            enable_btn  = gr.Button("✅ 使能全部")
            disable_btn = gr.Button("❌ 失能全部")
            start_btn   = gr.Button("▶️ 启动平衡控制")
            status_box  = gr.Textbox(label="状态", value=init_status, interactive=False)

            enable_btn.click(fn=enable_all, inputs=None, outputs=[status_box, log_box])
            disable_btn.click(fn=disable_all, inputs=None, outputs=[status_box, log_box])
            start_btn.click(fn=start_balance, inputs=None, outputs=[status_box, log_box])

        # 中间：位置控制
        with gr.Column():
            gr.Markdown("## 位置控制")
            pos1 = gr.Slider(0, 0.85, label="腿 1 位置")
            pos2 = gr.Slider(0, 0.85, label="腿 2 位置")
            pos3 = gr.Slider(0, 0.85, label="腿 3 位置")
            pos4 = gr.Slider(0, 0.85, label="腿 4 位置")
            vel = gr.Slider(0.1, 1.0, value=0.5, step=0.1, label="速度比例")
            set_btn = gr.Button("📍 设置位置")
            pos_status = gr.Textbox(label="位置设置结果", interactive=False)

            set_btn.click(fn=set_position,
                          inputs=[pos1, pos2, pos3, pos4, vel],
                          outputs=[pos_status, log_box])

        # 右侧：扭矩读取
        with gr.Column():
            gr.Markdown("## 扭矩读取")
            torque_output = gr.Textbox(label="腿部扭矩 (N/m)", interactive=False)
            read_btn = gr.Button("🔍 读取扭矩")
            read_btn.click(fn=get_torque, inputs=None, outputs=[torque_output, log_box])

    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)
