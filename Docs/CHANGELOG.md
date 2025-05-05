# Changelog

## [0.12.1] - 2025-May-05

- Overall site testing and updates.
- Main Readme udpated.

## [0.12.0] - 2025-May-01 - The Tech Expo

- Overall repository cleanup including renaming and reorganizing files, also updated all avaliable documentation.

## [0.10.0] - 2025-April-23

- Among other changes, added ESP32 support in the GUI.
- Ensured the API has now the correcty set static IPs and Port
- Readded ESP32 code.
- API now works with the 8 as a prefix, it is prepended to the dispense commands.
- Ensured the torch and pytorch versions to correcly work with the jetson.
  - torch==2.1.0
  - torchvision==0.16.0

## [0.7.0] - 2025-April-07

- Fixed Camera Detection using OpenCV
- Added Service Routine (H1) which will help constantly trigger the vending machine service mode.
- Check code for the logic, it is set to send "H1" every 20 seconds and the routine starts after first dispense request which is intended as for when the vending machine is set up.
- Fixed GUI status display

## [0.6.0] - 2025-April-07

- Renamed and Fully Updated Avend Mock Server, now uses JS to update the dashboard, as well as styling to be more modern and nicer.

## [0.5.0] - 2025-April-07

- Added IP Config to the Backup GUI
- Integrated PPE Buttons with the API
- Mock Server to display request history and details, also enabled auto-refresh every 3 seconds.

## [0.3.0] - 2025-April-04

- Added per session Cookie in the API code.
- Tested with actual kit over ethernet IP successfully.

## [0.2.0] - 2025-April-03

- Updated to PySide6
- Avend API Client and Mock Server

## [0.1.1] - 2025-March-28

- Implemented help page
- Updated best.pt
- Various Fixes with using PySide2

### Known Issue

- Not able to close application properly
  - Current Fix: Kill terminal or spam close app (alt+F4)

## [0.1.0-re] - 2025-March-27

- Rerelease.
