import time
from dm_imu import imu_py
from Legs_controller import LegsController


class PIDController:
    """
    独立 PID 控制器，用于单通道（pitch 或 roll）的控制。
    """
    def __init__(self, kp=0.0, ki=0.0, kd=0.0, integral_limit=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
    
    def reset(self):
        """重置 PID 状态。"""
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
    
    def set_params(self, kp, ki, kd, integral_limit=1.0):
        """设置 PID 参数。"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
    
    def compute(self, setpoint, measured_value, dt):
        """
        计算 PID 输出。
        
        Args:
            setpoint: 目标值（期望角度）
            measured_value: 实测值（当前角度）
            dt: 时间间隔（秒）
        
        Returns:
            PID 控制输出
        """
        error = setpoint - measured_value
        
        # 积分项，带限幅防止饱和
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        
        # 微分项（使用一阶差分）
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        
        # PID 输出
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        
        self.prev_error = error
        self.last_output = output
        return output
    
    def get_last_output(self):
        """获取上一次的控制输出值。"""
        return self.last_output


class BalanceController:
    """
    BalanceController 将原 balance.py 的平衡控制逻辑封装为类，
    复用 LegsController 中已实现的电机初始化、使能、失能、扭矩读取
    与位置控制等接口，保持脚本仍可直接运行。
    
    使用 PID 算法进行姿态平衡控制，支持动态参数调整。
    """

    def __init__(self, imu_port="/dev/dm-imu", imu_baud=921600, leg_port="/dev/dm-u2can"):
        # 实例化 LegsController（内部完成串口、MotorControl、所有电机的注册）
        # 若实际硬件不存在，LegsController 会在内部捕获异常，仍可安全实例化
        try:
            self.legs = LegsController(port=leg_port)
        except Exception as e:
            print(f"初始化 LegsController 失败: {e}")
            # 创建一个空对象，后续通过 getattr 检查其是否拥有 mc 属性
            self.legs = type('DummyLegs', (), {})()
        
        # 初始化 IMU（若硬件不可用则使用模拟对象）
        try:
            self.imu = imu_py.DmImu(imu_port, imu_baud)
            self.imu.start()
        except Exception as e:
            print(f"初始化 IMU 失败: {e}")
            class DummyImu:
                def getData(self):
                    # 返回零姿态以便算法继续运行
                    return {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
            self.imu = DummyImu()
        
        # 运行标志，控制主循环的退出
        self._running = False
        self._loop_started = False
        self.offs = [0.0, 0.0, 0.0, 0.0]
        
        # ========== PID 参数（类内部管理）==========
        # Pitch PID 控制器 (默认参数，可通过 set_pid 修改)
        self.pid_pitch = PIDController(kp=0.02, ki=0.001, kd=0.05, integral_limit=1.0)
        # Roll PID 控制器
        self.pid_roll = PIDController(kp=0.02, ki=0.001, kd=0.05, integral_limit=1.0)
        
        # ========== 可调参数（通过方法修改）==========
        self.wheel_vel = 12.0      # 默认轮子速度
        self.wheel_off_vel = 5.0   # 偏移调整时的轮子速度
        self.base_pos = 0.85       # 腿部基准位置
        self.max_vel = 1.0         # 最大速度限制
    
    def set_pid(self, kp_pitch, ki_pitch, kd_pitch, kp_roll, ki_roll, kd_roll):
        """
        设置 PID 参数。
        
        Args:
            kp_pitch: Pitch 比例系数
            ki_pitch: Pitch 积分系数
            kd_pitch: Pitch 微分系数
            kp_roll: Roll 比例系数
            ki_roll: Roll 积分系数
            kd_roll: Roll 微分系数
        """
        self.pid_pitch.set_params(kp_pitch, ki_pitch, kd_pitch)
        self.pid_roll.set_params(kp_roll, ki_roll, kd_roll)
        print(f"PID 参数已更新: Pitch=[{kp_pitch}, {ki_pitch}, {kd_pitch}], Roll=[{kp_roll}, {ki_roll}, {kd_roll}]")
    
    def set_wheel_velocity(self, vel, off_vel=None):
        """
        设置轮子速度参数。
        
        Args:
            vel: 主轮子速度（-1 到 1）
            off_vel: 偏移调整时的轮子速度（可选，默认为 vel）
        """
        self.wheel_vel = max(-1.0, min(1.0, vel))  # 限制在 -1 到 1
        if off_vel is not None:
            self.wheel_off_vel = max(-1.0, min(1.0, off_vel))
        else:
            self.wheel_off_vel = self.wheel_vel * 0.5
        print(f"轮子速度已更新: vel={self.wheel_vel}, off_vel={self.wheel_off_vel}")
    
    def set_leg_params(self, base_pos=None, max_vel=None):
        """
        设置腿部控制参数。
        
        Args:
            base_pos: 腿部基准位置（弧度）
            max_vel: 最大速度限制
        """
        if base_pos is not None:
            self.base_pos = max(0.1, min(2.0, base_pos))
        if max_vel is not None:
            self.max_vel = max(0.1, min(5.0, max_vel))
        print(f"腿部参数已更新: base_pos={self.base_pos}, max_vel={self.max_vel}")
    
    def reset_pid_state(self):
        """重置所有 PID 控制器的状态。"""
        self.pid_pitch.reset()
        self.pid_roll.reset()
        print("PID 状态已重置")

    # ---------- 电机管理 ----------
    def enable_all(self):
        """使能四条腿和四个轮子电机。"""
        if getattr(self.legs, "mc", None):
            self.legs.enable_legs()
            self.legs.enable_wheels()
        else:
            print("警告: LegsController 未成功初始化串口，跳过使能步骤。")

    def disable_all(self):
        """一次性失能所有电机（腿+轮子）。"""
        if getattr(self.legs, "mc", None):
            self.legs.disable_all()
        else:
            print("警告: LegsController 未成功初始化串口，跳过失能步骤。")

    # ---------- 状态读取 ----------
    def get_legs_torque(self):
        """返回四条腿电机的扭矩列表。"""
        if getattr(self.legs, "mc", None):
            return self.legs.get_legs_torque()
        else:
            print("警告: LegsController 未成功初始化串口，返回空列表。")
            return []

    # ---------- 位置控制 ----------
    def control_legs_pos(self, pos1, pos2, pos3, pos4, vel=None):
        """使用 LegsController 的位置‑速度控制四条腿。"""
        if getattr(self.legs, "mc", None):
            velocity = self.wheel_vel if vel is None else vel
            self.legs.control_legs_pos(pos1, pos2, pos3, pos4, velocity)
        else:
            print("警告: LegsController 未成功初始化串口，跳过位置控制。")
    
    def control_wheels_velocity(self, vel=None, off_vel=None):
        """直接控制轮子速度（用于平衡调整）。"""
        if getattr(self.legs, "mc", None):
            v = self.wheel_vel if vel is None else vel
            ov = self.wheel_off_vel if off_vel is None else off_vel
            self.legs.control_wheels_vel(v, ov)
        else:
            print("警告: LegsController 未成功初始化串口，跳过轮子速度控制。")

    # ---------- 私有工具 ----------
    def _limit_offsets(self, offs):
        """将偏置限制在 0~0.5 之间。"""
        return min(max(offs, 0.0), 0.5)

    def _update_offsets_with_pid(self, data, dt):
        """
        使用 PID 算法更新偏移量。
        
        Args:
            data: IMU 数据字典，包含 roll, pitch, yaw
            dt: 时间间隔（秒）
        
        Returns:
            更新后的 offs 列表
        """
        # Pitch 控制：影响前后腿的 offset
        pitch_output = self.pid_pitch.compute(0.0, data['pitch'], dt)
        
        # Roll 控制：影响左右腿的 offset
        roll_output = self.pid_roll.compute(0.0, data['roll'], dt)
        
        # 将 PID 输出转换为 offsets（对称调整）
        # Pitch: 前腿(+/-), 后腿(-/+)
        if data['pitch'] > 0:
            pitch_correction = abs(pitch_output) * 0.001
            self.offs[0] += pitch_correction  # 左前
            self.offs[1] += pitch_correction  # 右前
            self.offs[2] -= pitch_correction * 0.5  # 右后（减弱）
            self.offs[3] -= pitch_correction * 0.5  # 左后（减弱）
        else:
            pitch_correction = abs(pitch_output) * 0.001
            self.offs[2] += pitch_correction  # 右后
            self.offs[3] += pitch_correction  # 左后
            self.offs[0] -= pitch_correction * 0.5  # 左前（减弱）
            self.offs[1] -= pitch_correction * 0.5  # 右前（减弱）
        
        # Roll 控制：影响左右腿的 offset
        if data['roll'] > 0:
            roll_correction = abs(roll_output) * 0.001
            self.offs[1] += roll_correction  # 右前
            self.offs[2] += roll_correction  # 右后
            self.offs[0] -= roll_correction * 0.5  # 左前（减弱）
            self.offs[3] -= roll_correction * 0.5  # 左后（减弱）
        else:
            roll_correction = abs(roll_output) * 0.001
            self.offs[0] += roll_correction  # 左前
            self.offs[3] += roll_correction  # 左后
            self.offs[1] -= roll_correction * 0.5  # 右前（减弱）
            self.offs[2] -= roll_correction * 0.5  # 右后（减弱）
        
        # 归一化到 0~0.5 区间
        min_off = min(self.offs)
        self.offs = [o - min_off for o in self.offs]
        self.offs = [self._limit_offsets(o) for o in self.offs]
        
        return self.offs
    
    def _update_offsets_original(self, data, dt):
        """原始的偏移更新方法（保留兼容）。"""
        if data['pitch'] > 1:
            self.offs[0] = self.offs[0] + 0.0002 * (data['pitch'])
            self.offs[1] = self.offs[1] + 0.0002 * (data['pitch'])
        if data['pitch'] < -1:
            self.offs[2] = self.offs[2] + 0.0002 * (-data['pitch'])
            self.offs[3] = self.offs[3] + 0.0002 * (-data['pitch'])
        if data['roll'] < -1:
            self.offs[0] = self.offs[0] + 0.0001 * (-data['roll'])
            self.offs[3] = self.offs[3] + 0.0001 * (-data['roll'])
        if data['roll'] > 1:
            self.offs[1] = self.offs[1] + 0.0001 * (data['roll'])
            self.offs[2] = self.offs[2] + 0.0001 * (data['roll'])
        
        # 归一化到 0~0.5 区间
        min_off = min(self.offs)
        self.offs = [o - min_off for o in self.offs]
        self.offs = [self._limit_offsets(o) for o in self.offs]

        return self.offs

    # ---------- 主循环 ----------
    def run_balance_loop(self, use_pid=True):
        """
        运行平衡控制主循环。
        
        Args:
            use_pid: 是否使用 PID 算法（True=使用PID，False=使用原始阈值积分）
        """
        # 防止重复启动
        if self._loop_started:
            print("警告: 主循环已在运行中，跳过重复启动。")
            return
        
        self._running = True
        self._loop_started = True
        self.offs = [0.0, 0.0, 0.0, 0.0]
        prev_time = time.time()
        
        while self._running:
            try:
                cur_time = time.time()
                dt = cur_time - prev_time
                if dt <= 0:
                    # 防止除以零或极小 dt 导致的异常
                    dt = 1e-6
                prev_time = cur_time

                data = self.imu.getData()
                
                # 根据模式选择更新方法
                if use_pid:
                    self.offs = self._update_offsets_with_pid(data, dt)
                else:
                    self.offs = self._update_offsets_original(data, dt)

                if getattr(self.legs, "mc", None):
                    # 使用类内部的参数值
                    vel = min(self.wheel_vel, self.max_vel)
                    base_pos = self.base_pos
                    
                    # 控制腿部位置（调平）
                    self.control_legs_pos(
                        base_pos - self.offs[0],
                        base_pos - self.offs[1],
                        base_pos - self.offs[2],
                        base_pos - self.offs[3],
                        vel=vel,
                    )
                    
                    # 控制轮子速度（同时进行）
                    self.control_wheels_velocity(self.wheel_vel)
                else:
                    print(f"调试: 偏置计算结果 {self.offs}, roll={data['roll']:.2f}, pitch={data['pitch']:.2f}")

                #print(f"euler: (roll={data['roll']:.2f}, pitch={data['pitch']:.2f}, yaw={data['yaw']:.2f})")
                time.sleep(0.001)
            except Exception as e:
                print(f"平衡循环内部异常, 退出循环: {e}")
                break
        
        self._loop_started = False
    
    def stop_loop(self):
        """停止主循环。"""
        self._running = False

    # ---------- 收尾 ----------
    def shutdown(self):
        """关闭所有资源：失能电机、关闭串口、停止 IMU。"""
        # 先停止循环
        self.stop_loop()
        self.disable_all()
        # 若 LegsController 成功初始化串口则关闭，否则跳过
        if getattr(self.legs, "close_serial", None):
            try:
                self.legs.close_serial()
            except Exception as e:
                print(f"关闭串口时出现异常: {e}")
        # 若 imu_py 提供 stop 方法，可取消注释以下行
        # self.imu.stop()


def quick_test():
    """用于开发调试的快捷入口，手动调用时执行完整流程。"""
    controller = BalanceController()
    
    # 设置 PID 参数（示例值，需要根据实际调试调整）
    controller.set_pid(kp_pitch=0.5, ki_pitch=0.01, kd_pitch=0.1,
                      kp_roll=0.5, ki_roll=0.01, kd_roll=0.1)
    
    # 设置轮子速度
    controller.set_wheel_velocity(vel=12.0, off_vel=5.0)
    
    # 设置腿部参数
    controller.set_leg_params(base_pos=0.85, max_vel=1.0)
    
    controller.enable_all()
    controller.control_legs_pos(0.85, 0.85, 0.85, 0.85, vel=0.5)
    time.sleep(2)
    
    # 使用 PID 算法运行平衡循环
    controller.run_balance_loop(use_pid=True)
    
    controller.shutdown()

if __name__ == "__main__":
    print("请通过 UI 打开串口并控制机器人。")
