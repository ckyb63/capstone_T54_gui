# PPE A.I. Vending Machine

[![Latest Version](https://img.shields.io/badge/Log-v0.12.1-blue.svg)](CHANGELOG.md)
[![Python Version](https://img.shields.io/badge/Python-3.8.0+-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-31011/)
[![Maintainer](https://img.shields.io/badge/Maintainer-Max%20Chen-blue.svg)](https://github.com/ckyb63)
![Status](https://img.shields.io/badge/Status-Finished-darkgray.svg)

## Problem Statement

Ensuring factory-wide workplace PPE compliance is a significant challenge. Traditional monitoring through manual checks or signage frequently results in team injuries due to inadequate PPE usage. Our team has developed an intelligent vending machine system to combat this issue, utilizing AI camera technology to sense if a worker wears correct PPE and a deployment system to properly dispense missing items to them.

## Overview

This repository contains the codebase for the 2025-2026 Purdue Polytechnic Senior Capstone project, the PPE A.I. Vending Machine. This innovative solution combines computer vision, a user-friendly interface, and vending machine integration to ensure workplace safety compliance.

## Repository Components

- **AI Vision System**: Camera-based detection that determines if a user is PPE compliant
- **User Interface**: [PySide6-based GUI for system interaction](/vending_gui/main_gui.py)
- **Avend API**: [Integration with vending machine hardware](/avend_api_client/README.md)
- **Mock Server**: [Testing environment for vending machine functionality](/avend_mock_server/README.md)
- **Safety Gate Controller**: [ESP32-based system for dispensing control](/ESP32_Bluetooth_Comms/)

## Documentation

The [main gui](/vending_gui/main_gui.py) should be able to run on any system with Python 3.8.0+ installed, it will automatically try to establish connection with the Avend Kit and a USB connected ESP32, the Avend Kit should be able to auto-connect if the computer is plugged in the network switch, if it is not able to, then the hosting computer will need to configure its LAN IP address manually to:

- IPV4: 192.168.0.5
- Subnet Mask: 255.255.255.0
- DNS: 8.8.8.8

On GUI open, there will be warning popups telling if the Avend Kit servers or the ESP32 are not connected, it is fine if they aren't. For testing localy, ensure that the [Mock Server](/avend_mock_server/Avend_Server_Mock.py) is running and the IP is set to 127.0.0.1:8080.

The [camera opener](/vending_gui/camera_opener.py) is the module that handels opening a connected camera, it will attempt to loop through available devices until it opens one successfully, it will then attempt to load the trained model and start the detection thread. It is important that when using any camera with the Jetson that requires GStreamer, the OpenCV package is compiled with GStreamer support, this can be done by cloning the OpenCV source and compiling it with it enabled. Additionally, ensure that the PyTorch and TorchVision versions are compatible with the Jetson, the following versions were used and tested with the Jetson to enable CUDA support:

- torch==2.1.0
- torchvision==0.16.1

For running with the actual hardware, ensure that the Avend Kits are powered on (Blue Indicator Light), the ESP32 is properly connected via USB, and for the Vending machine to be in Service mode through pressing the service button. As this was a proof of concept, the main GUI was not written with proper error handeling, the Avend Kits will time out after around 5 minutes of inactivity, at which point if the GUI requests a dispense, it will crash and requires a software restart.

## Previous Software

Previous software developed with ROS 2 Humble integration can be found [here](https://github.com/ckyb63/ppe_gui_package).

## Acknowledgments

Packaging Systems of Indiana, a total corporation based in Lafayette, IN, for their support of this project.
