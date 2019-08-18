@echo off
echo %Date% %Time%: stocksAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\CHANG\AppData\Local\conda\conda\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksAnalyze.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time%: stocksAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log