import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
indexdata_path = os.path.join(root_path, "index_data")
resultfile_path = os.path.join(root_path, "lagging_Model_Select_Result.csv")
resultdata_path = os.path.join(root_path, "lagging_model_data")

def lagging_Model_Select():
    shangzhengIndex = "上证指数_0000001"
    shenchengIndex = "深证成指_1399001"
    with open(os.path.join(indexdata_path, (shangzhengIndex + ".csv"))) as fp:
        shangzheng_list = list(csv.reader(fp))
    with open(os.path.join(indexdata_path, (shenchengIndex + ".csv"))) as fp:
        shencheng_list = list(csv.reader(fp))
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        if((filename.split(".")[0].split("_"))[1][0]=="0"):
            index_list = shangzheng_list
        else:
            index_list = shencheng_list
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            stock_data_list = list(csv.reader(fp))
            laggingcounter = 0
            for ii in range(1, len(stock_data_list)):
                try:
                    if((float(stock_data_list[ii][9])>float(index_list[ii][9])) or (float(stock_data_list[ii][4])==float(stock_data_list[ii][5])) or (stock_data_list[ii][0] != index_list[ii][0])):
                        break
                    else:
                        laggingcounter += 1
                except:
                    break
            if(laggingcounter > 0):
                stockrange = 0
                indexrange = 0
                laggingrange = 0
                for ii in range(1, laggingcounter+1):
                    indexrange += float(index_list[ii][9])
                    stockrange += float(stock_data_list[ii][9])
                    laggingrange += float(index_list[ii][9]) - float(stock_data_list[ii][9])
                resultNumfile_path = os.path.join(resultdata_path,"lagging_Model_Select_Result"+str(laggingcounter)+".csv")
                if(not os.path.exists(resultNumfile_path)):
                    with open(resultNumfile_path, 'w') as fp:
                        row0 = "股票名称,"
                        for ii in range(1,laggingcounter+1):
                            row0 = row0 + "股票涨跌幅" + str(ii) + "," + "指数涨跌幅" + str(ii) + ","
                        row0 = row0 + "股票总涨跌幅" + "," + "指数总涨跌幅" + "," + "股票总滞后幅" + ","
                        fp.write(row0 + "\n")
                with open(resultNumfile_path, 'a') as fp:
                    datarow=filename+","
                    for ii in range(1, laggingcounter+1):
                        datarow = datarow + stock_data_list[ii][9] + "," + index_list[ii][9] + ","
                    datarow = datarow + str(stockrange) + "," + str(indexrange) + "," + str(laggingrange) + ","
                    fp.write(datarow + "\n")
                if(not os.path.exists(resultfile_path)):
                    with open(resultfile_path, 'w') as fp:
                        row0 = "股票名称, 股票滞后天数, 股票总滞后幅,"
                        fp.write(row0 + "\n")
                with open(resultfile_path, 'a') as fp:
                    datarow = filename+","+str(laggingcounter)+","+str(laggingrange) + ","
                    fp.write(datarow + "\n")


if __name__ == "__main__":
    filenames = os.listdir(root_path)
    for filename in filenames:
    	if(("lagging_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(root_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    filenames = os.listdir(resultdata_path)
    for filename in filenames:
        if(("lagging_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(resultdata_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    lagging_Model_Select()