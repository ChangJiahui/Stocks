import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
resultfile_path = os.path.join(root_path, "drop_Model_Select_Result.csv")
resultdata_path = os.path.join(root_path, "drop_model_data")

def drop_Model_Select():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            dropcounter = 0
            for ii in range(1, len(stock_data_list)):
                try:
                    if((float(stock_data_list[ii][9])>0) or (float(stock_data_list[ii][4])==float(stock_data_list[ii][5]))):
                        break
                    else:
                        dropcounter += 1
                except:
                    break
            if(dropcounter > 0):
                droprange2 = 0
                if(len(stock_data_list)>(dropcounter*3+1)):
                    for ii in range(1, dropcounter*3+1):
                        try:
                           droprange2 += float(stock_data_list[ii][9])
                        except:
                           continue
                if(droprange2>=0):
                    continue
                droprange = 0
                for ii in range(1, dropcounter+1):
                    droprange += float(stock_data_list[ii][9])
                resultNumfile_path = os.path.join(resultdata_path,"drop_Model_Select_Result"+str(dropcounter)+".csv")
                if(not os.path.exists(resultNumfile_path)):
                    with open(resultNumfile_path, 'w') as fp:
                        row0 = "股票名称,"
                        for ii in range(1,dropcounter+1):
                            row0 = row0 + "股票涨跌幅" + str(ii) + ","
                        row0 = row0 + "总涨跌幅" + ","
                        fp.write(row0 + "\n")
                with open(resultNumfile_path, 'a') as fp:
                    datarow=filename+","
                    for ii in range(1, dropcounter+1):
                        datarow = datarow + stock_data_list[ii][9] + ","
                    datarow = datarow + str(droprange) + ","
                    fp.write(datarow + "\n")
                if(not os.path.exists(resultfile_path)):
                	with open(resultfile_path, 'w') as fp:
                		row0 = "股票名称, 股票跌幅天数, 股票总涨跌幅,"
                		fp.write(row0 + "\n")
                with open(resultfile_path, 'a') as fp:
                	datarow = filename+","+str(dropcounter)+","+str(droprange) + ","
                	fp.write(datarow + "\n")


if __name__ == "__main__":
    filenames = os.listdir(root_path)
    for filename in filenames:
    	if(("drop_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(root_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    filenames = os.listdir(resultdata_path)
    for filename in filenames:
        if(("drop_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(resultdata_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    drop_Model_Select()