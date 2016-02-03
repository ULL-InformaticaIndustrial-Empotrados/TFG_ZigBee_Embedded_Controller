cmake_minimum_required(VERSION 2.8)

project(mir-server)

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread -g -std=c++14 -Werror -Wall -fno-strict-aliasing -pedantic -Wnon-virtual-dtor -Wextra -fPIC")

include_directories(
    ../stage/usr/include/mirserver
    ../stage/usr/include/mircommon
)

add_executable(
    mir-server

    mir_server.cpp
)

target_link_libraries(
    mir-server

    mirserver
)

install(TARGETS mir-server RUNTIME DESTINATION bin)
