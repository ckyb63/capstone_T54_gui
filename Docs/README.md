# PPE A.I. Vending Machine

[![Latest Version](https://img.shields.io/badge/Log-v0.12.0-blue.svg)](CHANGELOG.md)
[![Python Version](https://img.shields.io/badge/Python-3.10.11-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-31011/)
[![PySide6 Version](https://img.shields.io/badge/PySide6-6.9.0-blue.svg?logo=pyside&logoColor=white)](https://pypi.org/project/PySide6/)
![Status](https://img.shields.io/badge/Status-Finished-darkgray.svg)

## Problem Statement

Ensuring factory-wide workplace PPE compliance is a significant challenge. Traditional monitoring through manual checks or signage frequently results in team injuries due to inadequate PPE usage. Our team has developed an intelligent vending machine system to combat this issue, utilizing AI camera technology to sense if a worker wears correct PPE and a deployment system to properly dispense missing items to them.

## Overview

This repository contains the codebase for the 2025-2026 Purdue Polytechnic Senior Capstone project, the PPE A.I. Vending Machine. This innovative solution combines computer vision, a user-friendly interface, and vending machine integration to ensure workplace safety compliance.

## System Components

- **AI Vision System**: Camera-based detection that determines if a user is PPE compliant
- **User Interface**: PySide6-based GUI for system interaction
- **Avend API**: [Integration with vending machine hardware](/avend_api_client/README.md)
- **Mock Server**: [Testing environment for vending machine functionality](/avend_mock_server/README.md)
- **Safety Gate Controller**: [ESP32-based system for dispensing control](/ESP32_Bluetooth_Comms/)

## Final Design

Our solution produced a smart vending machine that detects if a user is PPE compliant. The final product is designed with workplace safety at its core and features:

- Real-time camera scan that identifies missing PPE items
- User-friendly interface with clear visual indicators
- Integrated safety gate system that ensures only required PPE items are dispensed
- Custom model trained to recognize specific PPE items

## Team Members

- Adrian Calderon
- Christopher Campbell
- Max Chen
- Aditya Prabhu
- Ryan Hay
- Cameron Johnson

## Acknowledgments

Packaging Systems of Indiana, a total corporation based in Lafayette, IN, for their support of this project.

## Future Work

- **Software Improvements**: The application could be further improved with public datasets
- **Model Optimization**: The computer vision model requires additional training on varied datasets for improved reliability
- **Hardware Enhancements**: Actual safety gate implementation requires strict adherence to relevant safety codes
