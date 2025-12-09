import time
from dm_imu_pkg import imu_py
from Legs_controller import LegsController

class BalanceController:
    """
    BalanceController 将原 balance.py 的平衡控制逻辑封装为类，
    复用 LegsController 中已实现的电机初始化、使能、失能、扭矩读取
    与位置控制等接口，保持脚本仍可直接运行。
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
    def control_legs_pos(self, pos1, pos2, pos3, pos4, vel=0.5):
        """使用 LegsController 的位置‑速度控制四条腿。"""
        if getattr(self.legs, "mc", None):
            self.legs.control_legs_pos(pos1, pos2, pos3, pos4, vel)
        else:
            print("警告: LegsController 未成功初始化串口，跳过位置控制。")

    # ---------- 私有工具 ----------
    def _limit_offsets(self, offs):
        """将偏置限制在 0~0.5 之间。"""
        return min(max(offs, 0.0), 0.5)

    def _update_offsets(self, data, dt):
        offs=[0.0,0.0,0.0,0.0]
        if data['pitch']>0.2:
            offs[0]=offs[0]+0.0001*(data['pitch'])*pow(data['pitch'],0.1)
            offs[1]=offs[1]+0.0001*(data['pitch'])*pow(data['pitch'],0.1)
        if data['pitch']<-0.2:
            offs[2]=offs[2]+0.0001*(-data['pitch'])*pow(-data['pitch'],0.1)
            offs[3]=offs[3]+0.0001*(-data['pitch'])*pow(-data['pitch'],0.1)
        if data['roll']<-0.2:
            offs[0]=offs[0]+0.0001*(-data['roll'])*pow(-data['roll'],0.1)
            offs[3]=offs[3]+0.0001*(-data['roll'])*pow(-data['roll'],0.1)
        if data['roll']>0.2:
            offs[1]=offs[1]+0.0001*(data['roll'])*pow(data['roll'],0.1)
            offs[2]=offs[2]+0.0001*(data['roll'])*pow(data['roll'],0.1)
		
        # 归一化到 0~0.5 区间
        min_off = min(offs)
        offs = [o - min_off for o in offs]
        offs = [self._limit_offsets(o) for o in offs]

        return offs

    # ---------- 主循环 ----------
    def run_balance_loop(self, max_vel=1.0):
        self._running = True
        offs = [0.0, 0.0, 0.0, 0.0]
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
                offs = self._update_offsets(data, dt)

                if getattr(self.legs, "mc", None):
                    vel = min(1.0, max_vel)
                    self.control_legs_pos(
                        0.85 - offs[0],
                        0.85 - offs[1],
                        0.85 - offs[2],
                        0.85 - offs[3],
                        vel=vel,
                    )
                else:
                    print("调试: 偏置计算结果", offs)

                #print(f"euler: (roll={data['roll']:.2f}, pitch={data['pitch']:.2f}, yaw={data['yaw']:.2f})")
                time.sleep(0.001)
            except Exception as e:
                print(f"平衡循环内部异常, 退出循环: {e}")
                break

    # ---------- 收尾 ----------
    def shutdown(self):
        """关闭所有资源：失能电机、关闭串口、停止 IMU。"""
        # 先停止循环
        self._running = False
        self.disable_all()
        # 若 LegsController 成功初始化串口则关闭，否则跳过
        if getattr(self.legs, "close_serial", None):
            try:
                self.legs.close_serial()
            except Exception as e:
                print(f"关闭串口时出现异常: {e}")
        # 若 imu_py 提供 stop 方法，可取消注释以下行
        # self.imu.stop()


if __name__ == "__main__":
    # 直接运行脚本时的入口
    controller = BalanceController()
    controller.enable_all()
    # 初始位置设置（与原脚本保持一致）
    controller.control_legs_pos(0.85, 0.85, 0.85, 0.85, vel=0.5)
    time.sleep(5)  # 与原脚本的延时保持一致
    # 进入平衡控制循环
    controller.run_balance_loop()
    # 结束后清理资源
    controller.shutdown()
