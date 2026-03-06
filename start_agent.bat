@echo off
cd /d D:\projects\shuai\ShuaiTravelAgent
D:\codes\anaconda3\envs\agents\python.exe -c "import os, sys; sys.path.insert(0, 'agent/src'); sys.path.insert(0, 'agent'); os.chdir('.'); from server import serve; serve()"
pause
