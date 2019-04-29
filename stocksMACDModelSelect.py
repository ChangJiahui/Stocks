import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
resultdata_path = os.path.join(root_path, "MACD_model_data")
resultfile_path = os.path.join(root_path, "MACD_Model_Select_Result.csv")

def MACD_Model_Select():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
#        print(filename)
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            dropcounter = 0
            EMA_12_list = [0]
            EMA_26_list = [0]
            DIFF_list = [0]
            DEA_9_list = [0]
            MACD_list = [0]
            for ii in reversed(range(1, len(stock_data_list))):
                try:
                    closing_price = float(stock_data_list[ii][3])
                except:
                    break
                EMA_12 = 11/13*EMA_12_list[-1] + 2/13*closing_price
                EMA_26 = 25/27*EMA_26_list[-1] + 2/27*closing_price
                DIFF = EMA_12 - EMA_26
                DEA_9 = 8/10*DEA_9_list[-1] + 2/10*DIFF
                MACD = (DIFF-DEA_9)*2
                EMA_12_list.append(EMA_12)
                EMA_26_list.append(EMA_26)
                DIFF_list.append(DIFF)
                DEA_9_list.append(DEA_9)
                MACD_list.append(MACD)
            if((DIFF_list[-2]<DEA_9_list[-2])&(DIFF_list[-1]>DEA_9_list[-1])&(DIFF_list[-1]<0)&(DEA_9_list[-1]<0)):
                if(os.path.exists(resultfile_path)):
                    with open(resultfile_path, 'w') as fp:
                        row0 = "股票名称,"
                        fp.write(row0 + "\n")
                with open(resultfile_path, 'a') as fp:
                    datarow = filename + ","
                    fp.write(datarow + "\n")


if __name__ == "__main__":
    filenames = os.listdir(root_path)
    for filename in filenames:
    	if(("MACD_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(root_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    MACD_Model_Select()