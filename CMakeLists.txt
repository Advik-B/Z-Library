cmake_minimum_required(VERSION 3.30)
project(Z_Library_Wrapper)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
#option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

option(USE_CPR "Use cpr library" ON)

file(GLOB_RECURSE SOURCES "src/*.cpp")
file(GLOB_RECURSE HEADERS "include/*.hpp")

add_library(z-library ${SOURCES} ${HEADERS}
        src/test.cpp
        include/test.hpp
        src/cpr_backend.cpp)

add_subdirectory(third_party/lexbor)

target_include_directories(z-library PUBLIC include)
target_link_libraries(z-library PRIVATE lexbor_static)

if(USE_CPR)
    include(FetchContent)
    FetchContent_Declare(cpr GIT_REPOSITORY https://github.com/libcpr/cpr.git
            GIT_TAG bb01c8db702fb41e5497aee9c0559ddf4bf13749) # Replace with your desired git commit from: https://github.com/libcpr/cpr/releases
    FetchContent_MakeAvailable(cpr)
    target_link_libraries(z-library PRIVATE cpr::cpr)
    target_compile_definitions(z-library PUBLIC USE_CPR)
endif()

#target_include_directories(z-library PUBLIC ${LEXBOR_SOURCE})

add_executable(z-library-test tests/main.cpp)
target_link_libraries(z-library-test z-library)
