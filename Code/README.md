
# 股票量化分析程序

** 清华大学 常嘉辉**

采用 Python 编写的可在 Windows 上定时运行的股票量化分析模型

## 源代码
+ stocksAnalyze.py (每日运行股票量化分析)
	+ Tunet 联网 （tunet.config）
	+ 每日网易股票数据下载更新
	+ 计算量化分析模型结果 （并行/非并行） *_Model_Select()
	+ 结果整理分析
	+ ……
+ stocksBackTest.py （股票量化模型回测）
	+ 下载股票历史数据
	+ 计算量化分析回测结果 *_Model_BackTest()
	+ ……
+ stocksDaily.py （分时运行股票量化分析）
	+ 开盘、午盘、收盘数据分析
	+ ……
+ stocksRealtime.py （每日实时监控大盘）
	+ 价格监控
	+ 量化交易提醒
	+ ……