# HUFI Viewer

A lightweight, standalone desktop GUI application for viewing, panning, zooming, and inspecting **.hufi** (Hagan's Ultimate Format for Images) files. Built with Python and Tkinter, HUFI Viewer delivers sub-millisecond header parsing and fast decompression with a clean, dark-mode visual layout.

## Features

- **Lossless Image Decoding:** Seamlessly renders `.hufi` files with 100% pixel accuracy.
- **Interactive Canvas:** Smooth panning (**Click + Drag**) and dynamic zooming (**Ctrl + Scroll** or **Ctrl + +/-**).
- **Metadata Inspector:** View image dimensions, color channels, header magic signature, and compressed payload size without opening external tools.
- **Windows Taskbar Integration:** Custom AppUserModelID registration ensures native icon display in the Windows Taskbar and title bar.
- **File Association Ready:** Configured for one-click default app assignment in Windows.

## Quickstart

### Download Executable (Windows)

Download the latest `HUFI-Viewer.exe` release from the Releases page or directly from the official website. Double-click `HUFI-Viewer.exe` to run—no installation required.
Double-click `HUFI-Viewer.exe` to run—no installation required.
#### Associating `.hufi` Files in Windows:
Right-click any `.hufi` file $\rightarrow$ Open with $\rightarrow$ Choose another app.
Browse and select `HUFI-Viewer.exe`.
Check "Always use this app to open .hufi files".
---
### Running from Source
#### Prerequisites
Python 3.8 or higher
Pillow (PIL)
#### Setup
Clone the repository:
```bash
   git clone https://github.com/your-username/hufi-viewer.git
   cd hufi-viewer
   ```
Install dependencies:
```bash
   pip install Pillow
   ```
Run the viewer:
```bash
   python main.py
   ```
---
### Building Executable from Source
To compile `main.py` into a single standalone `.exe` file using PyInstaller:
Install PyInstaller:
```bash
   pip install pyinstaller
   ```
Compile the binary:
```bash
   pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." main.py
   ```
The compiled standalone application will be generated inside the `dist/` folder as `main.exe` (or `HUFI_Viewer.exe`).

### Keyboard Shortcuts & Controls
Action	Shortcut / Control
Open File	`Ctrl + O`
Zoom In	`Ctrl + +` or `Ctrl + Mouse Wheel Up`
Zoom Out	`Ctrl + -` or `Ctrl + Mouse Wheel Down`
Reset Zoom (100%)	`Ctrl + 0`
Pan Image	`Left Click + Drag`
---
### License
Distributed under the Apache License, Version 2.0. See `LICENSE` for details.