#include "imu_driver.h"
#include <chrono>
#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>

#ifndef B460800
#define B460800 460800
#endif
#ifndef B921600
#define B921600 921600
#endif

namespace dmbot_serial
{

DmImu::DmImu(const std::string& port, int baud)
    : imu_serial_port(port), imu_seial_baud(baud), stop_thread_(false)
{
    // 初始化串口并完成 IMU 配置
    init_imu_serial();

    // 进入配置模式并初始化 IMU
    enter_setting_mode();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    turn_on_accel();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    turn_on_gyro();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    turn_on_euler();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    turn_off_quat();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    set_output_1000HZ();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    save_imu_para();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    exit_setting_mode();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
}

DmImu::~DmImu()
{
    stop();
    if (serial_fd >= 0)
    {
        close(serial_fd);
        serial_fd = -1;
    }
}

// -------------------------------
// Public API
// -------------------------------
bool DmImu::start()
{
    if (rec_thread.joinable())
    {
        // 已经在运行
        return true;
    }

    // 确保串口已打开
    if (serial_fd < 0)
    {
        init_imu_serial();
    }

    stop_thread_ = false;
    rec_thread = std::thread(&DmImu::get_imu_data_thread, this);
    return true;
}

void DmImu::stop()
{
    stop_thread_ = true;
    if (rec_thread.joinable())
    {
        rec_thread.join();
    }
    if (serial_fd >= 0)
    {
        close(serial_fd);
        serial_fd = -1;
    }
}

IMU_Data DmImu::getData() const
{
    std::lock_guard<std::mutex> lock(data_mutex);
    return data;
}

// -------------------------------
// Private implementation
// -------------------------------
void DmImu::init_imu_serial()
{
    // 打开串口
    serial_fd = open(imu_serial_port.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
    if (serial_fd < 0)
    {
        std::cerr << "Failed to open IMU serial port: " << imu_serial_port << std::endl;
        std::exit(EXIT_FAILURE);
    }

    // 配置波特率和串口属性
    struct termios tty;
    if (tcgetattr(serial_fd, &tty) != 0)
    {
        std::cerr << "Error from tcgetattr" << std::endl;
        std::exit(EXIT_FAILURE);
    }

    // 设置波特率
    speed_t speed;
    switch (imu_seial_baud)
    {
        case 115200: speed = B115200; break;
        case 230400: speed = B230400; break;
        case 460800: speed = B460800; break;
        case 921600: speed = B921600; break;
        default:
            std::cerr << "Unsupported baud rate: " << imu_seial_baud << std::endl;
            std::exit(EXIT_FAILURE);
    }
    cfsetospeed(&tty, speed);
    cfsetispeed(&tty, speed);

    // 8N1, 无硬件流控制
    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;     // 8 位字符
    tty.c_iflag &= ~IGNBRK;                         // 禁用 BREAK 处理
    tty.c_lflag = 0;                                // 无信号字符、回显、规范模式
    tty.c_oflag = 0;                                // 原始输出
    tty.c_cc[VMIN]  = 0;                            // 读取不阻塞
    tty.c_cc[VTIME] = 5;                            // 0.5 秒读取超时

    tty.c_cflag |= (CLOCAL | CREAD);                // 忽略调制解调器控制线，启用接收
    tty.c_cflag &= ~(PARENB | PARODD);              // 无奇偶校验
    tty.c_cflag &= ~CSTOPB;                         // 1 位停止位
    tty.c_cflag &= ~CRTSCTS;                        // 无硬件流控制

    if (tcsetattr(serial_fd, TCSANOW, &tty) != 0)
    {
        std::cerr << "Error from tcsetattr" << std::endl;
        std::exit(EXIT_FAILURE);
    }

    std::cout << "IMU serial port opened successfully." << std::endl;
}

// -------------------------------
// 配置指令（与原始 ROS 代码保持一致，仅去掉 ros::Duration）
// -------------------------------
void DmImu::enter_setting_mode()
{
    uint8_t txbuf[4] = {0xAA, 0x06, 0x01, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::turn_on_accel()
{
    uint8_t txbuf[4] = {0xAA, 0x01, 0x14, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::turn_on_gyro()
{
    uint8_t txbuf[4] = {0xAA, 0x01, 0x15, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::turn_on_euler()
{
    uint8_t txbuf[4] = {0xAA, 0x01, 0x16, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::turn_off_quat()
{
    uint8_t txbuf[4] = {0xAA, 0x01, 0x07, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::set_output_1000HZ()
{
    uint8_t txbuf[5] = {0xAA, 0x02, 0x01, 0x00, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::save_imu_para()
{
    uint8_t txbuf[4] = {0xAA, 0x03, 0x01, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::exit_setting_mode()
{
    uint8_t txbuf[4] = {0xAA, 0x06, 0x00, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void DmImu::restart_imu()
{
    uint8_t txbuf[4] = {0xAA, 0x00, 0x00, 0x0D};
    for (int i = 0; i < 5; ++i)
    {
        write(serial_fd, txbuf, sizeof(txbuf));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

// -------------------------------
// 数据采集线程
// -------------------------------
void DmImu::get_imu_data_thread()
{
    int error_num = 0;
    while (!stop_thread_)
    {
        if (serial_fd < 0)
        {
            std::cerr << "IMU serial port not open in data thread." << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }

        // 读取完整帧（共 57 字节）
        ssize_t len = read(serial_fd, &receive_data, sizeof(receive_data));
        if (len != static_cast<ssize_t>(sizeof(receive_data)))
        {
            ++error_num;
            continue;
        }

        // 验证帧头
        if (receive_data.FrameHeader1 == 0x55 && receive_data.flag1 == 0xAA &&
            receive_data.slave_id1 == 0x01 && receive_data.reg_acc == 0x01)
        {
            // CRC 校验并提取数据
            if (Get_CRC16(reinterpret_cast<uint8_t*>(&receive_data.FrameHeader1), 16) == receive_data.crc1)
            {
                data.accx = *reinterpret_cast<float*>(&receive_data.accx_u32);
                data.accy = *reinterpret_cast<float*>(&receive_data.accy_u32);
                data.accz = *reinterpret_cast<float*>(&receive_data.accz_u32);
            }
            if (Get_CRC16(reinterpret_cast<uint8_t*>(&receive_data.FrameHeader2), 16) == receive_data.crc2)
            {
                data.gyrox = *reinterpret_cast<float*>(&receive_data.gyrox_u32);
                data.gyroy = *reinterpret_cast<float*>(&receive_data.gyroy_u32);
                data.gyroz = *reinterpret_cast<float*>(&receive_data.gyroz_u32);
            }
            if (Get_CRC16(reinterpret_cast<uint8_t*>(&receive_data.FrameHeader3), 16) == receive_data.crc3)
            {
                data.roll  = *reinterpret_cast<float*>(&receive_data.roll_u32);
                data.pitch = *reinterpret_cast<float*>(&receive_data.pitch_u32);
                data.yaw   = *reinterpret_cast<float*>(&receive_data.yaw_u32);
            }

            // 线程安全更新共享数据
            {
                std::lock_guard<std::mutex> lock(data_mutex);
                // data 已在上面更新，无需额外操作
            }
        }
        else
        {
            ++error_num;
            if (error_num > 1200)
            {
                std::cerr << "Failed to find correct IMU frame header (0x55)." << std::endl;
                error_num = 0;
            }
        }
    }
}

}
