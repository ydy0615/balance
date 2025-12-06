import time
import numpy as np
import serial
import imu_py  # Real IMU wrapper
from .DM_CAN import Motor, MotorControl, DM_Motor_Type
from cpg import CPGController

# -------------------------------------------------------------------------------
# 硬件初始化（串口、IMU、四条腿电机）
# -------------------------------------------------------------------------------
serial_dev = None
imu = None
motor_ctrl = None
motors = {}

# 全局滑动窗口，用于对 IMU 原始数据进行低通滤波（移动平均）
_pitch_window = []
_yaw_window = []
_roll_window = []
_WINDOW_SIZE = 5  # 窗口长度，可根据噪声水平调节

def _moving_average(window, new_value):
    """将 new_value 加入窗口并返回窗口均值"""
    window.append(new_value)
    if len(window) > _WINDOW_SIZE:
        window.pop(0)
    return float(np.mean(window))

def _init_hardware():
    """
    初始化真实硬件：
    - 串口用于 CAN 总线
    - IMU（pybind_imu）提供陀螺仪角速度
    - 四条腿电机对象并使能
    """
    global serial_dev, imu, motor_ctrl, motors

    # 1. 串口（根据实际设备路径修改）
    serial_dev = serial.Serial('/dev/ttyACM1', 921600, timeout=0.5)

    # 2. IMU（使用 pybind_imu 包）
    imu = imu_py.DmImu("/dev/ttyACM0", 921600)
    imu.start()

    # 3. 电机控制对象
    motor_ctrl = MotorControl(serial_dev)

    # 4. 创建四条腿电机实例（DM4340 为示例型号，可根据实际更改）
    Motor1 = Motor(DM_Motor_Type.DM4340, 0x01, 0x11)
    Motor2 = Motor(DM_Motor_Type.DM4340, 0x02, 0x12)
    Motor3 = Motor(DM_Motor_Type.DM4340, 0x03, 0x13)
    Motor4 = Motor(DM_Motor_Type.DM4340, 0x04, 0x14)

    # 5. 将电机加入控制器并使能
    motor_ctrl.addMotor(Motor1)
    motor_ctrl.addMotor(Motor2)
    motor_ctrl.addMotor(Motor3)
    motor_ctrl.addMotor(Motor4)

    motor_ctrl.enable(Motor1)
    motor_ctrl.enable(Motor2)
    motor_ctrl.enable(Motor3)
    motor_ctrl.enable(Motor4)

    # 6. 保存到全局字典，便于后续索引
    motors = {
        'Motor1': Motor1,
        'Motor2': Motor2,
        'Motor3': Motor3,
        'Motor4': Motor4
    }

# -------------------------------------------------------------------------------
# 主循环：读取 IMU → 更新 CPG → 发送电机指令
# -------------------------------------------------------------------------------
def run(duration: float = 60.0, dt: float = 0.01):
    """
    运行四足平衡控制，使用真实 IMU 数据。
    :param duration: 运行时长（秒）
    :param dt: 控制循环时间步长（秒）
    """
    # 硬件初始化（只在第一次调用时执行）
    if serial_dev is None or imu is None or motor_ctrl is None:
        _init_hardware()

    # 使用更长的基准周期以降低振荡频率（原 1.0 s → 2.0 s）
    controller = CPGController(base_height=0.0,
                              base_period=2.0,
                              amplitude=0.85,
                              stable_range=6.0)

    # 初始位置：Motor1、Motor4 在 -0.85，Motor2、Motor3 在 +0.85
    h1 = -0.85
    h2 = 0.85
    h3 = 0.85
    h4 = -0.85
    t = 0.0
    print(f"t={t:.2f}s deviation={0.0:.3f} "
          f"h1={h1:.3f} h2={h2:.3f} h3={h3:.3f} h4={h4:.3f}")
    motor_ctrl.control_Pos_Vel(motors['Motor1'], h1, 12)
    motor_ctrl.control_Pos_Vel(motors['Motor2'], h2, 12)
    motor_ctrl.control_Pos_Vel(motors['Motor3'], h3, 12)
    motor_ctrl.control_Pos_Vel(motors['Motor4'], h4, 12)

    # 保持初始位置一段时间后再开始 CPG 循环
    time.sleep(0.5)

    # 重置时间计数
    start_time = time.time()
    # 将 CPG 时间同步到最高点，以保持平滑运动
    controller.t = controller.base_period / 4

    while time.time() - start_time < duration:
        # 1️⃣ 从真实 IMU 读取角速度（单位：度/秒）
        data = imu.getData()
        pitch_raw = data.get('gyroy', 0.0)
        yaw_raw   = data.get('gyroz', 0.0)
        roll_raw  = data.get('gyrox', 0.0)

        # 对原始 IMU 数据进行移动平均滤波
        pitch_rate = _moving_average(_pitch_window, pitch_raw)
        yaw_rate   = _moving_average(_yaw_window,   yaw_raw)
        roll_rate  = _moving_average(_roll_window,  roll_raw)

        print(f"IMU data: pitch_rate={pitch_rate:.3f}, yaw_rate={yaw_rate:.3f}, roll_rate={roll_rate:.3f}")

        # 2️⃣ CPG 步进，更新四条腿的目标高度，返回偏差用于调试
        deviation = controller.step(pitch_rate, yaw_rate, dt)

        # 3️⃣ 读取四条腿的目标高度（范围在 [-0.85, 0.85]）
        heights = controller.get_leg_heights()   # {'FL':h1, 'FR':h2, 'RL':h3, 'RR':h4}

        # 4️⃣ 将高度映射到电机指令范围（结合 CPG 输出和 IMU 角速度进行微调，保持最高点）
        #   - 基准高度：Motor1、Motor4 为 -0.85，Motor2、Motor3 为 +0.85
        #   - factor_cpg 控制 CPG 微调幅度（默认 0.2）
        #   - factor_imu 控制俯仰/偏航角速度反馈幅度（默认 0.05）
        #   - factor_roll 控制横滚（左右倾斜）反馈幅度（已增大至 0.12）
        factor_cpg = 0.2
        factor_imu = 0.05
        factor_roll = 0.12

        # 基于 IMU 角速度的额外微调
        imu_correction_1 = -factor_imu * pitch_rate - factor_imu * yaw_rate - factor_roll * roll_rate   # Motor1
        imu_correction_2 =  factor_imu * pitch_rate + factor_imu * yaw_rate + factor_roll * roll_rate   # Motor2
        imu_correction_3 =  factor_imu * pitch_rate - factor_imu * yaw_rate + factor_roll * roll_rate   # Motor3
        imu_correction_4 = -factor_imu * pitch_rate + factor_imu * yaw_rate - factor_roll * roll_rate   # Motor4

        # 将 CPG 输出（heights）与基准高度、IMU 修正相结合后进行裁剪
        h1 = np.clip(-0.85 + factor_cpg * heights['FL'] + imu_correction_1, -0.85, 0.0)   # Motor1 负向
        h2 = np.clip( 0.85 + factor_cpg * heights['FR'] + imu_correction_2, 0.0, 0.85)   # Motor2 正向
        h3 = np.clip( 0.85 + factor_cpg * heights['RL'] + imu_correction_3, 0.0, 0.85)   # Motor3 正向
        h4 = np.clip(-0.85 + factor_cpg * heights['RR'] + imu_correction_4, -0.85, 0.0)   # Motor4 负向

        # 5️⃣ 调试输出（显示实际发送给电机的高度，已裁剪到合法区间）
        t = time.time() - start_time
        print(f"t={t:.2f}s deviation={deviation:.3f} "
              f"h1={h1:.3f} h2={h2:.3f} h3={h3:.3f} h4={h4:.3f}")

        # 6️⃣ 发送位置指令
        motor_ctrl.control_Pos_Vel(motors['Motor1'], h1, 12)
        motor_ctrl.control_Pos_Vel(motors['Motor2'], h2, 12)
        motor_ctrl.control_Pos_Vel(motors['Motor3'], h3, 12)
        motor_ctrl.control_Pos_Vel(motors['Motor4'], h4, 12)

        # 7️⃣ 控制循环频率
        time.sleep(dt)

    # ------------------- 安全停机 -------------------
    for m in motors.values():
        motor_ctrl.disable(m)
    if serial_dev:
        serial_dev.close()
    if imu:
        imu.stop()
