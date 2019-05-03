import os
import csv

stock_info = "万业企业_0600641"
root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "Data", "stock_data_history")
with open(os.path.join(stockdata_path,'{}.csv'.format(stock_info)), 'r+') as fp:                                 #保存数据
    stock_data_list = list(csv.reader(fp))
#    for ii in reversed(range(1, len(stock_data_list))):
#        if(len(stock_data_list[ii])!=15):
#            print(stock_data_list[ii])
#            stock_data_list.pop(ii)
#            continue
#        if(float(stock_data_list[ii][3])==0):
#            print(stock_data_list[ii])
#            stock_data_list.pop(ii)
#            continue
    for ii in reversed(range(1, len(stock_data_list))):
    	if(len(stock_data_list[ii])!=15):
    	    print(stock_data_list[ii])
    for ii in reversed(range(1, len(stock_data_list))):
        if(float(stock_data_list[ii][3])==0):
#            print(stock_data_list[ii])
            stock_data_list.pop(ii)
    for ii in reversed(range(1, len(stock_data_list))):
    	if(len(stock_data_list[ii])!=15):
    	    print(stock_data_list[ii])