@echo off
echo %Date% %Time% stocksTools.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksTools.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\.conda\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksTool.py
echo %Date% %Time% stocksTools.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksTools.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log