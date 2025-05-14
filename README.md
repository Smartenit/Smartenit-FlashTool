# ESP Flash Tool

## Overview

The ESP Flash Tool is a user-friendly application designed to simplify the process of flashing firmware to ESP32/ESP8266 microcontrollers. It provides a graphical interface for selecting firmware files, configuring flash parameters, and monitoring serial output.

## Features

- **Port Selection**: Choose from available serial ports
- **Baud Rate Configuration**: Set communication speed (default 460800)
- **File Management**: 
  - Add individual binary files
  - Load complete configurations via `flasher_args.json`
- **Flash Operations**: One-click flashing with configurable parameters
- **Serial Monitor**: 
  - Real-time monitoring
  - Pause/resume functionality
- **Data Logging**: Save manufacturing data to CSV for analysis
- **Intuitive UI**: Simple interface with clear section organization

## Requirements

- Python 3.10 or later
- Git
- pip and virtualenv
- GUI support (needed if running on a headless system like Raspberry Pi OS Lite)
- Python dependencies:
  - `tkinter` (installed via system package manager)
  - `pyserial`
  - `esptool`

### Run the application:

python esp_flash_tool.py

### Basic Usage
- Connect your ESP device via USB

- Select the correct COM port from the dropdown

- Configure flash settings:

  Set baud rate (default 460800)

  Add firmware files manually or via flasher_args.json

  Click "Flash Device" to program your microcontroller

- Monitor output using the built-in serial monitor

### Advanced Features
-  JSON Configuration: Use flasher_args.json for complex flash setups

-  Manufacturing Data Collection: Automatic parsing and storage of mfg data

-  CSV Logging: Save serial output and manufacturing data for analysis

### Setting Steps

1. **Install Git and clone the repository:**
   
```bash
   sudo apt update
   sudo apt install git
   git clone https://github.com/Smartenit/Smartenit-FlashTool.git
 ```
2. Navigate to the project folder:
```bash
   cd Smartenit-FlashTool/
 ```
3. Install the modules and libreries:
   
   - Steps for Windows:
```bash
    pip install tk
    pip install pyserial esptool
 ```
   - Steps for Linux/Ubuntu/Debian:
```bash
    sudo usermod -aG dialout $USER 
    newgrp dialout
    sudo apt install python3-tk 
    python3 -m venv venv 
    source venv/bin/activate
    pip install pyserial esptool
 ```
4. Run the application:
   ```bash
    python esp_flash_toolv2.py
    ```
### Setting Steps
1. Windows, access the folder and run:
      ```bash
    python esp_flash_toolv2.py
    ```
3. Linux:
      ```bash
    source venv/bin/activate
    python esp_flash_toolv2.py
    ```
