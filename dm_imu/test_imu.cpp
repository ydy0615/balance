#include "imu_driver.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <fstream>

int main()
{
    // 根据实际设备路径与波特率创建 IMU 对象
    dmbot_serial::DmImu imu("/dev/ttyACM0", 921600);

    // 启动采集线程
    if (!imu.start())
    {
        std::cerr << "Failed to start IMU driver." << std::endl;
        return 1;
    }

    // 打开 CSV 文件用于保存数据
    std::ofstream csvFile("dm_imu/imu_data.csv");
    csvFile << "index,roll,pitch,yaw,accx,accy,accz,gyrox,gyroy,gyroz\n";

    // 示例：读取 1000 次数据（约 10 秒，100 Hz）
    for (int i = 0; i < 1000; ++i)
    {
        dmbot_serial::IMU_Data data = imu.getData();

        std::cout << "Roll: " << data.roll << "  Pitch: " << data.pitch
                  << "  Yaw: " << data.yaw << std::endl;
        std::cout << "Acc  : [" << data.accx << ", " << data.accy << ", " << data.accz << "]"
                  << std::endl;
        std::cout << "Gyro : [" << data.gyrox << ", " << data.gyroy << ", " << data.gyroz << "]"
                  << std::endl;
        std::cout << "----------------------------------------" << std::endl;

        // 写入 CSV
        csvFile << i << ',' << data.roll << ',' << data.pitch << ',' << data.yaw << ','
                << data.accx << ',' << data.accy << ',' << data.accz << ','
                << data.gyrox << ',' << data.gyroy << ',' << data.gyroz << '\n';

        // 10 ms 间隔（约 100 Hz）
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    csvFile.close();

    // 停止采集并关闭串口
    imu.stop();
    std::system("python3 dm_imu/plot_imu.py");

    return 0;
}
