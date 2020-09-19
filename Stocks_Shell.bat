@echo off
echo %Date% %Time%: stocksAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksAnalyze.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time%: stocksAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log
TIMEOUT /T 10 /NOBREAK
echo %Date% %Time%: fundsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: fundsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\fundsAnalyze.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time%: fundsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: fundsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log
TIMEOUT /T 10 /NOBREAK
echo %Date% %Time%: bondsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: bondsAnalyze.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\bondsAnalyze.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time%: bondsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: bondsAnalyze.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log
TIMEOUT /T 10 /NOBREAK
echo %Date% %Time%: stocksTrade.py Program Run! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksTrade.py Program Run! >> D:\Workspace\Python\Stocks\Error.log
C:\Users\Chang\anaconda3\envs\Stocks\python.exe D:\Workspace\Python\Stocks\Code\stocksTrade.py 1>>D:\Workspace\Python\Stocks\Logger.log 2>>D:\Workspace\Python\Stocks\Error.log
echo %Date% %Time%: stocksTrade.py Program Finished! >> D:\Workspace\Python\Stocks\Logger.log
echo %Date% %Time%: stocksTrade.py Program Finished! >> D:\Workspace\Python\Stocks\Error.log