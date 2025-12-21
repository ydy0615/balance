import math
from DM_CAN import *
import serial
import time
import imu_py

Motor1=Motor(DM_Motor_Type.DM4340,0x01,0x11)
Motor2=Motor(DM_Motor_Type.DM4340,0x02,0x12)
Motor3=Motor(DM_Motor_Type.DM4340,0x03,0x13)
Motor4=Motor(DM_Motor_Type.DM4340,0x04,0x14)

Wheel1=Motor(DM_Motor_Type.DMH6215,0x05,0x15)
Wheel2=Motor(DM_Motor_Type.DMH6215,0x06,0x16)
Wheel3=Motor(DM_Motor_Type.DMH6215,0x07,0x17)
Wheel4=Motor(DM_Motor_Type.DMH6215,0x08,0x18)

serial_device = serial.Serial('/dev/ttyACM1', 921600, timeout=0.5)
imu = imu_py.DmImu("/dev/ttyACM0", 921600)
imu.start()

MC1=MotorControl(serial_device)
MC1.addMotor(Motor1)
MC1.addMotor(Motor2)
MC1.addMotor(Motor3)
MC1.addMotor(Motor4)

MC1.enable(Motor1)
MC1.enable(Motor2)
MC1.enable(Motor3)
MC1.enable(Motor4)
i=0

print(Motor1.getTorque())
print(Motor2.getTorque())
print(Motor3.getTorque())
print(Motor4.getTorque())

time.sleep(0.01)

MC1.control_Pos_Vel(Motor1,-0.85,0.5)
MC1.control_Pos_Vel(Motor2,0.85,0.5)
MC1.control_Pos_Vel(Motor3,0.85,0.5)
MC1.control_Pos_Vel(Motor4,-0.85,0.5)

print("#####################")

time.sleep(5)

self.offs1=0.0
self.offs2=0.0
self.offs3=0.0
self.offs4=0.0
for i in range(1,10000):
    MC1.control_Pos_Vel(Motor1,-0.85+self.offs1,12)
    MC1.control_Pos_Vel(Motor2,0.85-self.offs2,12)
    MC1.control_Pos_Vel(Motor3,0.85-self.offs3,12)
    MC1.control_Pos_Vel(Motor4,-0.85+self.offs4,12)

    data = imu.getData()
    if data['pitch']>0.2:
        self.offs1=self.offs1+0.0001*(data['pitch'])*pow(data['pitch'],0.5)
        self.offs2=self.offs2+0.0001*(data['pitch'])*pow(data['pitch'],0.5)
    if data['pitch']<-0.2:
        self.offs3=self.offs3+0.0001*(-data['pitch'])*pow(-data['pitch'],0.5)
        self.offs4=self.offs4+0.0001*(-data['pitch'])*pow(-data['pitch'],0.5)
    if data['roll']<-0.2:
        self.offs1=self.offs1+0.0001*(-data['roll'])*pow(-data['roll'],0.2)
        self.offs4=self.offs4+0.0001*(-data['roll'])*pow(-data['roll'],0.2)
    if data['roll']>0.2:
        self.offs2=self.offs2+0.0001*(data['roll'])*pow(data['roll'],0.2)
        self.offs3=self.offs3+0.0001*(data['roll'])*pow(data['roll'],0.2)
    add = min(self.offs1,self.offs2,self.offs3,self.offs4)
    self.offs1=self.offs1-add
    self.offs2=self.offs2-add
    self.offs3=self.offs3-add
    self.offs4=self.offs4-add
    if self.offs1>0.5: self.offs1=0.5
    if self.offs2>0.5: self.offs2=0.5
    if self.offs3>0.5: self.offs3=0.5
    if self.offs4>0.5: self.offs4=0.5
    print(f"euler: (roll={data['roll']:.2f}, pitch={data['pitch']:.2f}, yaw={data['yaw']:.2f})")
    print(self.offs3,self.offs4,self.offs1,self.offs2,data['pitch'])
    time.sleep(0.001)

MC1.disable(Wheel1)
MC1.disable(Wheel2)
MC1.disable(Wheel3)
MC1.disable(Wheel4)

MC1.refresh_motor_status(Motor1)
MC1.refresh_motor_status(Motor2)
MC1.refresh_motor_status(Motor3)
MC1.refresh_motor_status(Motor4)

time.sleep(0.1)

print(Motor1.getTorque())
print(Motor2.getTorque())
print(Motor3.getTorque())
print(Motor4.getTorque())

MC1.control_Pos_Vel(Motor1,0.0,0.5)
MC1.control_Pos_Vel(Motor2,0.0,0.5)
MC1.control_Pos_Vel(Motor3,0.0,0.5)
MC1.control_Pos_Vel(Motor4,0.0,0.5)

time.sleep(3)

MC1.disable(Motor1)
MC1.disable(Motor2)
MC1.disable(Motor3)
MC1.disable(Motor4)


serial_device.close()
# imu.stop()