cmake_minimum_required(VERSION 3.30)
project(Z_Library_Wrapper)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
#option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

file(GLOB_RECURSE SOURCES "src/*.cpp")
file(GLOB_RECURSE HEADERS "include/*.hpp")

add_library(z-library ${SOURCES} ${HEADERS}
        src/test.cpp
        include/test.hpp)

add_subdirectory(third_party/lexbor)

target_include_directories(z-library PUBLIC include)
target_link_libraries(z-library lexbor_static)
#target_include_directories(z-library PUBLIC ${LEXBOR_SOURCE})

add_executable(z-library-test tests/main.cpp)
target_link_libraries(z-library-test z-library)
