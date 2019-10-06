
# 简单的股票量化分析模型

** 清华大学 常嘉辉**

采用 Python 编写的可在 Windows 上定时运行的股票量化分析模型

(记得自己记好 AccountBook 哦~)

## 数据目录 （没有则自动建立）
+ BackTest：回测程序结果
    + *_Model_BackTest_Result.csv
+ Data：每日下载更新股票数据
    + AB_stock_data
		+ (stockinfo).csv
	+ AB_stock_data_history
		+ (yyyymmdd).csv
	+ AH_stock_data
		+ (stockinfo).csv
	+ AH_stock_data_history
		+ (yyyymmdd).csv
	+ index_data
		+ （AS指数.csv）
	+ stock_data
		+ (stockinfo).csv
	+ stock_gdzjc
		+ (stockinfo).csv
	+ （中证规模指数）.xls
	+ fund_data
		+ (fundinfo).csv
	+ stockinfo.txt
	+ fundinfo.txt
+ Daily：每日股票实盘分析
	+ yyyymmdd
		+ *_select.csv
+ Result：量化模型分析结果
	+ yyyymmdd
		+ *_select.csv
+ Code：运行及测试代码
	+ stocksAnalyze.py (每日运行股票量化分析)
	+ stocksBackTest.py （股票量化模型回测）
	+ stocksDaily.py （分时运行股票量化分析）
	+ stocksRealtime.py （每日实时监控大盘）
	+ fundsAnalyze.py (每日运行基金量化分析)

## 自动运行 bat：
- Stocks_Shell.bat： 运行每日股票分析程序 stocksAnalyze.py
- StocksNoon_Shell.bat： 运行股票分时分析程序 stocksDaily.py
- Funds_Shell.bat： 运行每日基金分析程序 fundsAnalyze.py