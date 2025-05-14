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

- Python 3.7+
- Supported operating systems: Windows, Linux, macOS

### Required Packages

pip install pyserial pandas tkinter

### Installation
Clone the repository or download the source files:

git clone [repository-url]

### Install dependencies:
pip install -r requirements.txt

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
