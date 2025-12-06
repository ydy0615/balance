cmake_minimum_required(VERSION 3.14)
project(imu_py LANGUAGES CXX)

# 使用 C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找 pybind11（已通过 pip 安装）
# 添加 CMake 前缀路径，使 CMake 能找到 pybind11 的配置文件
set(CMAKE_PREFIX_PATH "/home/allenyuan/.local/lib/python3.10/site-packages/pybind11/share/cmake" ${CMAKE_PREFIX_PATH})

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/..
    /home/allenyuan/.local/lib/python3.10/site-packages/pybind11/include
)

find_package(pybind11 REQUIRED)

pybind11_add_module(imu_py
    pybind_imu.cpp
    ../dm_imu/imu_driver.cpp
    ../dm_imu/bsp_crc.cpp)

target_link_libraries(imu_py PRIVATE pthread)
