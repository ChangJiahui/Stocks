@echo off
echo %Date% %Time% stocksTools.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksTools.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksTools.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time% stocksTools.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time% stocksTools.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log