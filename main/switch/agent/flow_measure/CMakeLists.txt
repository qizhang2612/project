cmake_minimum_required(VERSION 3.16)
project(flow_measure)

set(CMAKE_CXX_STANDARD 17)
set(CXX_FLAGS -m64 -pthread -march=native -g2 -ggdb -Wall)

set(CMAKE_BUILD_TYPE RelWithDebInfo)
set(CMAKE_BUILD_TYPE Debug)
set(MESSAGE ${CMAKE_SOURCE_DIR}/message)
set(LIB ${CMAKE_SOURCE_DIR}/lib)
aux_source_directory(${LIB} lib_files)
aux_source_directory(${MESSAGE} msg_files)

add_compile_options(${CXX_FLAGS})
find_package( TBB REQUIRED)
find_package(glog REQUIRED)
add_executable(flow_measure main.cc ${lib_files} ${msg_files})
target_link_libraries(flow_measure pcap TBB::tbb pthread glog::glog)