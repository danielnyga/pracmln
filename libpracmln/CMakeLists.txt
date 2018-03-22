cmake_minimum_required(VERSION 2.8.3)
project(libpracmln)

#####################
## Default options ##
#####################

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING
      "Choose the type of build, options are: None Debug Release RelWithDebInfo MinSizeRel."
      FORCE)
endif(NOT CMAKE_BUILD_TYPE)

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  set(CMAKE_INSTALL_PREFIX "${PROJECT_SOURCE_DIR}/install" CACHE PATH "Install path for project" FORCE)
endif(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)

###############
## CXX Flags ##
###############

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DBT_USE_DOUBLE_PRECISION -Wall")
# Unused warnings
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wuninitialized -Winit-self -Wunused-function -Wunused-label -Wunused-variable -Wunused-but-set-variable -Wunused-but-set-parameter")
# Additional warnings
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Warray-bounds -Wtype-limits -Wreturn-type -Wsequence-point -Wparentheses -Wmissing-braces -Wchar-subscripts -Wswitch -Wwrite-strings -Wenum-compare -Wempty-body -Wlogical-op")

##################
## Dependencies ##
##################

## System dependencies are found with CMake's conventions


message(STATUS $ENV{PYTHONDIST})

if("$ENV{PYTHONDIST}" MATCHES "2.")
  set(PYTHONVERSION, "2.7")  
  find_package(Boost REQUIRED COMPONENTS python)
elseif("$ENV{PYTHONDIS}" MATCHES "3.")
  set(PYTHONVERSION, "3.5")
  find_package(Boost REQUIRED COMPONENTS python-py35)
endif("$ENV{PYTHONDIST}" MATCHES "2.")

find_package(PythonLibs ${PYTHONVERSION} REQUIRED)

if(NOT PYTHONLIBS_FOUND)
  message(ERROR "PythonLibs not found!")
endif()


message(STATUS ${Boost_LIBRARIES})

##################
## Header files ##
##################

# Display additional files in qtcreator
add_custom_target(header_files SOURCES
  include/pracmln/mln.h
)

###########
## Build ##
###########

include_directories(
  include
  ${Boost_INCLUDE_DIRS}
  ${PYTHON_INCLUDE_DIRS}
)

add_library(pracmln SHARED src/mln.cpp)
target_link_libraries(pracmln
  ${Boost_LIBRARIES}
  ${PYTHON_LIBRARIES}
)

add_definitions(-DPROJECT_SRC_DIR="${PROJECT_SOURCE_DIR}")
add_executable(test_mln src/test_mln.cpp)
target_link_libraries(test_mln pracmln)

#############
## Install ##
#############

install(DIRECTORY "${PROJECT_SOURCE_DIR}/include" DESTINATION ${CMAKE_INSTALL_PREFIX})

install(TARGETS pracmln
  RUNTIME DESTINATION bin
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
)
