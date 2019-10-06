@echo off
echo %Date% %Time%: fundsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\FundsLogger.log
echo %Date% %Time%: fundsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\FundsError.log
C:\Users\CHANG\AppData\Local\conda\conda\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\fundsAnalyze.py 1>>D:\Workspace\Python\Stocks\FundsLogger.log 2>>D:\Workspace\Python\Stocks\FundsError.log
echo %Date% %Time%: fundsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\FundsLogger.log
echo %Date% %Time%: fundsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\FundsError.log