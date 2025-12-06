#ifndef _IMU_DRIVER_H_
#define _IMU_DRIVER_H_
#include <iostream>
#include <thread>
#include <initializer_list>
#include <fstream>
#include <array>
#include <mutex>
#include <atomic>
#include <math.h>
#include "bsp_crc.h"

namespace dmbot_serial
{
#pragma pack(1)
typedef struct
{
    uint8_t FrameHeader1;
    uint8_t flag1;
    uint8_t slave_id1;
    uint8_t reg_acc;
    uint32_t accx_u32;
    uint32_t accy_u32;
    uint32_t accz_u32;
    uint16_t crc1;
    uint8_t FrameEnd1;

    uint8_t FrameHeader2;
    uint8_t flag2;
    uint8_t slave_id2;
    uint8_t reg_gyro;
    uint32_t gyrox_u32;
    uint32_t gyroy_u32;
    uint32_t gyroz_u32;
    uint16_t crc2;
    uint8_t FrameEnd2;

    uint8_t FrameHeader3;
    uint8_t flag3;
    uint8_t slave_id3;
    uint8_t reg_euler; // r-p-y
    uint32_t roll_u32;
    uint32_t pitch_u32;
    uint32_t yaw_u32;
    uint16_t crc3;
    uint8_t FrameEnd3;
} IMU_Receive_Frame;
#pragma pack()

typedef struct
{
    float accx;
    float accy;
    float accz;
    float gyrox;
    float gyroy;
    float gyroz;
    float roll;
    float pitch;
    float yaw;
} IMU_Data;

class DmImu
{
public:
    DmImu(const std::string& port = "/dev/ttyACM1", int baud = 921600);
    ~DmImu();

    // Start data acquisition thread; returns true on success
    bool start();
    // Stop acquisition and close serial port
    void stop();

    // Get latest IMU data (thread‑safe copy)
    IMU_Data getData() const;

private:
    void init_imu_serial();
    void get_imu_data_thread();

    void enter_setting_mode();
    void turn_on_accel();
    void turn_on_gyro();
    void turn_on_euler();
    void turn_off_quat();
    void set_output_1000HZ();
    void save_imu_para();
    void exit_setting_mode();
    void restart_imu();

    int imu_seial_baud;
    std::string imu_serial_port;
    int serial_fd = -1;
    std::thread rec_thread;
    mutable std::mutex data_mutex;
    bool stop_thread_ = false;

    IMU_Receive_Frame receive_data{};
    IMU_Data data{};
};

}
#endif
