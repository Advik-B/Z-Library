cmake_minimum_required(VERSION 3.30)
project(Z_Library)

set(CMAKE_CXX_STANDARD 20)

file(GLOB_RECURSE SOURCES "src/*.cpp")
file(GLOB_RECURSE HEADERS "include/*.hpp")

add_executable(Z_Library ${SOURCES} ${HEADERS})
