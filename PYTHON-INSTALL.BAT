@echo Off
REM Installs the BlueLinky Python packages
pip install .
py -m compileall py-src
py -m compileall py-src/bluelinky
