# -----------------------------------------------------------------------------
#
# Copyright (C) 2021 CERN & University of Surrey for the benefit of the
# BioDynaMo collaboration. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# See the LICENSE file distributed with this work for details.
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# -----------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.19.3)
project(skibidy)

# BioDynaMo curretly uses the C++17 standard.
set(CMAKE_CXX_STANDARD 17)

# Use BioDynaMo in this project.
find_package(BioDynaMo REQUIRED)

# See UseBioDynaMo.cmake in your BioDynaMo build folder for details.
# GoogleTest may come from a test-enabled BioDynaMo installation or the
# system development package (the standalone BioDynaMo installer disables tests).
include(${BDM_USE_FILE})

# Consider all files in src/ and modules/ for BioDynaMo simulation.
include_directories("src")
include_directories("modules")
include_directories("third_party")

# Auto-discover study module directories (studies/*/modules/).
# Biologists add modules here without editing CMakeLists.txt.
file(GLOB STUDY_MODULE_DIRS "studies/*/modules")
foreach(STUDY_DIR ${STUDY_MODULE_DIRS})
    include_directories("${STUDY_DIR}")
endforeach()

# The hook registry must exist before BioDynaMo configures its ROOT dictionary.
# Config merging is a separate consumer and cannot be a build prerequisite.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(STUDY_HOOK_SCRIPT "${CMAKE_SOURCE_DIR}/scripts/config/gen_study_hooks.py")
set(STUDY_HOOK_HEADER "${CMAKE_SOURCE_DIR}/src/core/study_hooks_gen.h")
file(GLOB STUDY_HOOK_DECLS CONFIGURE_DEPENDS
     "${CMAKE_SOURCE_DIR}/studies/*/modules/study_hooks.decl")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
             "${STUDY_HOOK_SCRIPT}" ${STUDY_HOOK_DECLS})
execute_process(COMMAND "${Python3_EXECUTABLE}" "${STUDY_HOOK_SCRIPT}"
                RESULT_VARIABLE STUDY_HOOK_RESULT
                OUTPUT_VARIABLE STUDY_HOOK_OUTPUT
                ERROR_VARIABLE STUDY_HOOK_ERROR)
if(NOT STUDY_HOOK_RESULT EQUAL 0)
    message(FATAL_ERROR "Study hook generation failed: ${STUDY_HOOK_OUTPUT}${STUDY_HOOK_ERROR}")
endif()
add_custom_command(OUTPUT "${STUDY_HOOK_HEADER}"
                   COMMAND "${Python3_EXECUTABLE}" "${STUDY_HOOK_SCRIPT}"
                   DEPENDS "${STUDY_HOOK_SCRIPT}" ${STUDY_HOOK_DECLS}
                   COMMENT "Generating study hook registry"
                   VERBATIM)
add_custom_target(${CMAKE_PROJECT_NAME}-study-hooks DEPENDS "${STUDY_HOOK_HEADER}")

file(GLOB_RECURSE PROJECT_HEADERS src/*.h modules/*.h)
# Include study module headers in the build
foreach(STUDY_DIR ${STUDY_MODULE_DIRS})
    file(GLOB_RECURSE STUDY_HEADERS "${STUDY_DIR}/*.h")
    list(APPEND PROJECT_HEADERS ${STUDY_HEADERS})
endforeach()
file(GLOB_RECURSE PROJECT_SOURCES src/*.cc)

# main.cc lives at project root (outside src/) so libskibidy.so has no
# main() symbol -- the test binary provides its own gtest main instead.
bdm_add_executable(${CMAKE_PROJECT_NAME}
                   HEADERS ${PROJECT_HEADERS}
                   SOURCES ${PROJECT_SOURCES} ${CMAKE_SOURCE_DIR}/main.cc
                   LIBRARIES ${BDM_REQUIRED_LIBRARIES})
add_dependencies(${CMAKE_PROJECT_NAME} ${CMAKE_PROJECT_NAME}-study-hooks)

# Optimize for the build machine's native CPU in Release builds
if(CMAKE_BUILD_TYPE STREQUAL "Release" OR NOT CMAKE_BUILD_TYPE)
    target_compile_options(${CMAKE_PROJECT_NAME} PRIVATE -march=native)
endif()

# Consider all files in tests/ for GoogleTests.
# Note: we avoid bdm_add_test / gtest_discover_tests because BioDynaMo's
# CommandLineOptions parser rejects --gtest_list_tests at discovery time.
# Using gtest_add_tests (source-based discovery) instead.
include_directories("tests")
file(GLOB_RECURSE TEST_SOURCES tests/*.cc)
file(GLOB_RECURSE TEST_HEADERS tests/*.h)
# Auto-discover study-scoped tests (studies/*/tests/*.cc)
foreach(STUDY_DIR ${STUDY_MODULE_DIRS})
    get_filename_component(STUDY_PARENT "${STUDY_DIR}" DIRECTORY)
    file(GLOB_RECURSE STUDY_TEST_SOURCES "${STUDY_PARENT}/tests/*.cc")
    list(APPEND TEST_SOURCES ${STUDY_TEST_SOURCES})
endforeach()

find_path(SKIBIDY_GTEST_INCLUDE_DIR gtest/gtest.h
          HINTS "$ENV{BDMSYS}/include" REQUIRED)
find_library(SKIBIDY_GTEST_LIBRARY NAMES gtest
             HINTS "$ENV{BDMSYS}/lib" REQUIRED)
add_library(libgtest IMPORTED STATIC GLOBAL)
set_target_properties(libgtest PROPERTIES
    IMPORTED_LOCATION "${SKIBIDY_GTEST_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${SKIBIDY_GTEST_INCLUDE_DIR}"
    IMPORTED_LINK_INTERFACE_LIBRARIES "${CMAKE_THREAD_LIBS_INIT}")

add_executable(${CMAKE_PROJECT_NAME}-test ${TEST_SOURCES})
target_link_libraries(${CMAKE_PROJECT_NAME}-test
                      ${BDM_REQUIRED_LIBRARIES} ${CMAKE_PROJECT_NAME} libgtest)
# Register as a single test -- BioDynaMo's CommandLineOptions parser rejects
# --gtest_filter and --gtest_list_tests, so per-test CTest entries don't work.
add_test(NAME ${CMAKE_PROJECT_NAME}-tests
         COMMAND ${CMAKE_PROJECT_NAME}-test)
