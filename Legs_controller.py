import math
import time
import serial
from u2can.DM_CAN import (
    Motor, MotorControl,
    DM_Motor_Type, Control_Type, DM_variable
)

class LegsController:
    """
    简单的达妙腿部/轮子控制类，只实现基本的初始化、使能、
    失能、扭矩读取以及位置控制。
    """

    def __init__(self, port="/dev/dm-u2can", baudrate=921600, timeout=0.5):
        """打开串口、创建 MotorControl、实例化并注册所有电机。"""
        self.serial_device = serial.Serial(port, baudrate, timeout=timeout)
        self.mc = MotorControl(self.serial_device)

        # 四条腿电机（DM4340）
        self.motor1 = Motor(DM_Motor_Type.DM4340, 0x01, 0x11)
        self.motor2 = Motor(DM_Motor_Type.DM4340, 0x02, 0x12)
        self.motor3 = Motor(DM_Motor_Type.DM4340, 0x03, 0x13)
        self.motor4 = Motor(DM_Motor_Type.DM4340, 0x04, 0x14)

        # 四个轮子电机（DMH6215）
        self.wheel1 = Motor(DM_Motor_Type.DMH6215, 0x05, 0x15)
        self.wheel2 = Motor(DM_Motor_Type.DMH6215, 0x06, 0x16)
        self.wheel3 = Motor(DM_Motor_Type.DMH6215, 0x07, 0x17)
        self.wheel4 = Motor(DM_Motor_Type.DMH6215, 0x08, 0x18)

        # 注册所有电机
        for m in (self.motor1, self.motor2, self.motor3, self.motor4,
                  self.wheel1, self.wheel2, self.wheel3, self.wheel4):
            self.mc.addMotor(m)

    # ---------- 串口管理 ----------
    def open_serial(self):
        """重新打开已关闭的串口（如果需要）。"""
        if not self.serial_device.is_open:
            self.serial_device.open()

    def close_serial(self):
        """关闭串口，释放资源。"""
        if self.serial_device.is_open:
            self.serial_device.close()

    # ---------- 使能 ----------
    def enable_legs(self):
        """使能四条腿电机。"""
        for m in (self.motor1, self.motor2, self.motor3, self.motor4):
            self.mc.enable(m)

    def enable_wheels(self):
        """使能四个轮子电机。"""
        for w in (self.wheel1, self.wheel2, self.wheel3, self.wheel4):
            self.mc.enable(w)

    def disable_all(self):
        """一次性失能所有电机（腿+轮子）。"""
        for m in (self.motor1, self.motor2, self.motor3, self.motor4,
                  self.wheel1, self.wheel2, self.wheel3, self.wheel4):
            self.mc.disable(m)

    # ---------- 状态读取 ----------
    def get_legs_torque(self):
        """刷新四条腿的状态并返回它们的扭矩列表。"""
        for m in (self.motor1, self.motor2, self.motor3, self.motor4):
            self.mc.refresh_motor_status(m)
        return [
            self.motor1.getTorque(),
            self.motor2.getTorque(),
            self.motor3.getTorque(),
            self.motor4.getTorque(),
        ]

    # ---------- 位置控制 ----------
    def control_legs_pos(self, pos1, pos2, pos3, pos4, vel=0.5):
        """
        使用位置‑速度模式控制四条腿。
        参数:
            pos1‑pos4: 目标位置（单位依据电机规格）
            vel:      速度比例，默认 0.5
        """
        self.mc.control_Pos_Vel(self.motor1, -pos1, vel)
        self.mc.control_Pos_Vel(self.motor2,  pos2, vel)
        self.mc.control_Pos_Vel(self.motor3,  pos3, vel)
        self.mc.control_Pos_Vel(self.motor4, -pos4, vel)
    
    def control_wheels_vel(self,vel,of_vel):
        self.mc.control_Vel(self.wheel1,-(vel+of_vel))
        self.mc.control_Vel(self.wheel2,(vel-of_vel))
        self.mc.control_Vel(self.wheel3,-(vel-of_vel))
        self.mc.control_Vel(self.wheel4,(vel+of_vel))