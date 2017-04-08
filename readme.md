# AlertStockVol

## Alert the Stock Volume Change

Use tushare module to monitor the a real-time periodic volume change for a series of stocks. If the change value is greater than a certain percentage of last trade-day's whole volume, the user is altered by a taskbar and caption flash under windows system.

## GUI
The simple GUI is written with tkinter and the author will not promise any efficiency.

## Build
Use pyinstaller to build the windows executable file. The building procedure has been tested for python 3. Version 3.6 is NOT supported by pyinstaller!!!

Try the command below to get rid of console:
~~~~
pyinstaller --onefile --noconsole alert_gui_class.py
~~~~
