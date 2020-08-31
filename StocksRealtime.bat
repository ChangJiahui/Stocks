@echo off
echo %Date% %Time% stocksRealtime.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksRealtime.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\.conda\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksRealtime.py
echo %Date% %Time% stocksRealtime.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksRealtime.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log