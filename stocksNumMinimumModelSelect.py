import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
resultfile_path = os.path.join(root_path, "minimum_Model_Select_Result.csv")

def minimum_Model_Select():
    with open("minimum_Model_Select_Result.csv", 'w') as fp:
        fp.write("股票名称,最低价天数,收盘价天数," + "\n")
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            closing_minimumdays = 0
            least_minimumdays = 0
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            try:
                stock_least_price = float(stock_data_list[1][5])
                stock_closing_price = float(stock_data_list[1][3])
                if(stock_closing_price==0):
                    closing_minimumdays = 0
                    continue
                if(stock_least_price==0):
                    least_minimumdays = 0
                    continue
                for ii in range(2, len(stock_data_list)+1):
                    if(float(stock_data_list[ii][3]==0)):
                        continue
                    elif(stock_closing_price < float(stock_data_list[ii][3])):
                        closing_minimumdays += 1
                    else:
                        break
                for ii in range(2, len(stock_data_list)+1):
                    if(float(stock_data_list[ii][3]==0)):
                        continue
                    elif(stock_least_price < float(stock_data_list[ii][3])):
                        least_minimumdays += 1
                    else:
                        break
            except:
                closing_minimumdays = 0
                least_minimumdays = 0
                continue
            with open(resultfile_path, 'a') as fp:
                datarow=filename+"," + str(least_minimumdays) + "," + str(closing_minimumdays) + "," 
                fp.write(datarow + "\n")


if __name__ == "__main__":
    minimum_Model_Select()