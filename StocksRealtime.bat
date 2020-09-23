@echo off
echo %Date% %Time% stocksRealtime.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksRealtime.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksRealtime.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time% stocksRealtime.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksRealtime.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log