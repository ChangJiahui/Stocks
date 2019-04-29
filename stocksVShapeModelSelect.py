import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
resultfile_path = os.path.join(root_path, "vshape_Model_Select_Result.csv")
resultdata_path = os.path.join(root_path, "vshape_model_data")

def vshape_Model_Select():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            riserange = 0
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            try:
                if(float(stock_data_list[1][9])<0):
                    continue
            except:
                continue
            dropcounter = 0
            for ii in range(2, len(stock_data_list)):
                try:
                    if(float(stock_data_list[ii][9])>0):
                        break
                    else:
                        dropcounter += 1
                except:
                    break
            if(dropcounter > 0):
                droprange = 0
                for ii in range(2, dropcounter+2):
                    droprange += float(stock_data_list[ii][9])
                resultNumfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result"+str(dropcounter)+".csv")
                if(not os.path.exists(resultNumfile_path)):
                    with open(resultNumfile_path, 'w') as fp:
                        row0 = "股票名称,"
                        for ii in range(1,dropcounter+1):
                            row0 = row0 + "股票跌幅" + str(ii) + ","
                        row0 = row0 + "总跌幅" + "," + "股票涨幅" + ","
                        fp.write(row0 + "\n")
                with open(resultNumfile_path, 'a') as fp:
                    datarow=filename+","
                    for ii in range(2, dropcounter+2):
                        datarow = datarow + stock_data_list[ii][9] + ","
                    datarow = datarow + str(droprange) + "," + stock_data_list[1][9] + ","
                    fp.write(datarow + "\n")
                if(not os.path.exists(resultfile_path)):
                	with open(resultfile_path, 'w') as fp:
                		row0 = "股票名称, 股票跌幅天数, 股票总跌幅,股票涨幅,"
                		fp.write(row0 + "\n")
                with open(resultfile_path, 'a') as fp:
                	datarow = filename+","+str(dropcounter)+","+str(droprange) + "," + stock_data_list[1][9]
                	fp.write(datarow + "\n")


if __name__ == "__main__":
    filenames = os.listdir(root_path)
    for filename in filenames:
    	if(("vshape_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(root_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    filenames = os.listdir(resultdata_path)
    for filename in filenames:
        if(("vshape_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(resultdata_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    vshape_Model_Select()