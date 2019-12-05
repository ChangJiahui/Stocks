
# 简单的股票量化分析模型

** 清华大学 常嘉辉**

采用 Python 编写的可在 Windows 上定时运行的股票量化分析模型

(记得自己记好 AccountBook 哦~)

## 数据目录 （没有则自动建立）
+ BackTest：回测程序结果
    + *_Model_BackTest_Result.csv
+ Data：每日下载更新股票数据
	+ daily_data
		+ noon_data.csv
		+ night_data.csv
	+ fund_data
		+ (fundinfo).csv
	+ index_data
		+ （指数.csv）
    + margin_data
		+ (stockinfo).csv
		+ yyyymmdd.csv
	+ stock_data
		+ (stockinfo).csv
	+ stock_gdzjc
		+ (stockinfo).csv
	+ stockB_data
		+ (yyyymmdd).csv
		+ (stockinfo).csv
	+ stockHK_data
		+ (yyyymmdd).csv
		+ (stockinfo).csv
	+ （中证规模指数）.xls
	+ stockinfo.txt
	+ fundinfo.txt
+ Result：量化模型分析结果
	+ Stocks
		+ *_select.csv
		+ EHBF_Analyze_Result.csv
		+ summary_result.csv
	+ Daily
		+ *_select.csv
	+ Funds
		+ *_select.csv
	+ Query
		+ (stockinfo).csv
	+ Tools
		+ *_select.csv
+ Code：运行及测试代码
	+ stocksAnalyze.py (每日运行股票量化分析)
	+ fundsAnalyze.py (每日运行基金量化分析)
	+ stocksTrade.py (每日运行持仓股票分析)
	+ stocksDaily.py （每日运行盘面分析）
	+ stocksRealtime.py （实时监控大盘）
	+ stocksBackTest.py （股票量化模型回测）
	+ stocksTools.py （股票长周期选股工具）
	+ tunet

## 自动运行 bat：
- Stocks_Shell.bat： 运行每日股票基金分析程序 stocksAnalyze.py
- StocksNoon_Shell.bat： 运行股票每日盘面分析程序 stocksDaily.py