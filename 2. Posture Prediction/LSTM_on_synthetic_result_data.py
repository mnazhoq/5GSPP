# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 09:38:15 2023

@author: umroot
"""
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib.pyplot as plt
from pandas import datetime
import math, time
from sklearn import preprocessing
import datetime
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers.recurrent import LSTM
from keras.models import load_model
import keras
import h5py
import requests
import os
import csv
import random

# Input data files are available in the "../input/" directory.
# For example, running this (by clicking run or pressing Shift+Enter) will list the files in the input directory



# Any results you write to the current directory are saved as output.
# data_path = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\My Implementation Resources\\synthetic_result_data_only_posture.csv"   
data_path_comb_goal = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\\From Mahmood\\SourceCode\\data_for_exp_combGoal_22Feb.csv"   
data_path_TokImp = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\\From Mahmood\\SourceCode\\data_for_exp_TokenImp_22Feb.csv"   
data_path_Exfiltrate = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\\From Mahmood\\SourceCode\\data_for_exp_ExfData_23Feb.csv"




#read csv file
# data_df  = pd.read_csv(data_path_Exfiltrate)
# data_df.dropna(inplace=True) #remove empty rows
# print(data_df.head())
#create column with same values
# data_df.posturevalue = 0.98 #set all values of the column to 0.97
# plt.plot(data_df['posturevalue'])
# plt.title('data of posture_value_goal_node')
# plt.show()
# data_df.index = data_df['Time']
# print(data_df.head())


#define constants
NO_OF_ROWS = 10000
CHANGE_RATES_VALUEs = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
loop_back_variable = 5 #sliding window size
DIR = os.path.dirname(os.path.abspath(__file__))

#create dataframe with one column named "pattern" with pattern values
pattern_values = [0.98, 0.89, 0.83, 0.71, 0.63, 0.54, 0.45, 0.35, 0.15]
df = pd.DataFrame({'pattern': pattern_values * NO_OF_ROWS})

#create column with same values
df["same"] = 0.98

###### This function generate synthetic data within the changeRate 
def generateSynthDataWithinRate (df, colName = "chnageRate", changeRate = 0.2):
   
      
    # Create a sample DataFrame (replace with your actual data)
    if df.empty:
        data = {'original_column': [10, 20, 30, 40, 50]}
        df = pd.DataFrame(data)
    
    # Set the desired threshold for average difference
    threshold = changeRate  # Adjust as needed
    changeRate = 1-changeRate
    
    # Generate random values within a range (e.g., 0 to 100)
    # df[colName] = np.random.rand(len(df))
    df[colName] = [random.uniform(changeRate, 1.0) for _ in range(len(df))]
    # df['random_values'] = np.random.choice([0, 1], size=len(df), p=[0.1, 0.9])
    
    # Calculate differences between consecutive values
    df['differences'] = df[colName].diff(loop_back_variable) #diff has two parameters axes
    # df['differences'] = df[colName].pct_change() #Computes the fractional change from the immediately previous row by default
    
    # Check if average difference is below the threshold
    while df['differences'].mean() > threshold:
        # df[colName] = np.random.rand(len(df))
        df[colName] = [random.uniform(changeRate, 1.0) for _ in range(len(df))]
        df['differences'] = df[colName].diff(loop_back_variable)
        # df['differences'] = df[colName].pct_change() #Computes the fractional change from the immediately previous row by default
        print("Mean diff: ", df['differences'].mean())
        
    # Now 'random_values' contains valid random values
    print(df[[colName, 'differences']])


#create columns with different change rate
for changeRate in CHANGE_RATES_VALUEs: 
    colName = "chnageRate_" + str(changeRate)
    generateSynthDataWithinRate(df, colName, changeRate)

#remove the difference column
df = df.drop('differences', axis=1)

#save the data in a csv file
app1_data_file = os.path.join(DIR, '5GSPP_data_Ap1_dif_5.csv')
df.to_csv(app1_data_file)
# data_df['Time'] = pd.to_datetime(data_df['date_time'])

#csv file to store results
all_result_file = os.path.join(DIR, '5GSPP_results_PostVal_dif_5.csv')

columns_res=["valueType", "slidingWind", "RMSE_train", "RMSE", "MAE", "r2", "trainingTime", "predTime"]

if os.path.exists(all_result_file) == False:#if not exist file create it
  with open (all_result_file, 'a') as filedata: 
    writer = csv.writer(filedata, delimiter=',')
    writer.writerow(columns_res)
    
    
# convert an array of values into a dataset matrix
def create_dataset(dataset, look_back=loop_back_variable):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

def train_model(df, colName):
    
    #pre-process dataset
    min_max_scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
    dataset = min_max_scaler.fit_transform(df[colName].values.reshape(-1, 1))
    # print(dataset[0:10])

    # split into train and test sets
    train_size = int(len(dataset) * 0.7)
    test_size = len(dataset) - train_size
    train, test = dataset[0:train_size,:], dataset[train_size:len(dataset),:]
    print(len(train), len(test))
    
    x_train, y_train = create_dataset(train, look_back=loop_back_variable)
    x_test, y_test = create_dataset(test, look_back=loop_back_variable)

    x_train = np.reshape(x_train, (x_train.shape[0], 1, x_train.shape[1]))
    x_test = np.reshape(x_test, (x_test.shape[0], 1, x_test.shape[1]))
    
    print("x_train shape: ", x_train.shape)
    print("y_train shape: ", y_train.shape)
    print("x_test shape: ", x_test.shape)
    print("y_test shape: ", y_test.shape)
    
    training_start_time = time.time();
    # create and fit the LSTM network
    model = Sequential()
    model.add(LSTM(20, input_shape=(1, loop_back_variable)))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam', metrics=['accuracy'])
    history = model.fit(x_train, y_train, epochs=5, batch_size=1, verbose=2, validation_split=0.05, shuffle=True).history
    
    training_time = time.time() - training_start_time;
    print('Training_time: ', training_time)
    
    
    # ------------------Draw figure of accuracy and loss
    plt.plot(history['accuracy'])
    plt.plot(history['val_accuracy'])
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.show()
    # -------------------
    
    trainPredict = model.predict(x_train)
    testPredict = model.predict(x_test)
    # invert predictions
    trainPredict = min_max_scaler.inverse_transform(trainPredict)
    trainY = min_max_scaler.inverse_transform([y_train])
    testPredict = min_max_scaler.inverse_transform(testPredict)
    testY = min_max_scaler.inverse_transform([y_test])
    
    # calculate root mean squared error
    trainRMSE = math.sqrt(mean_squared_error(trainY[0], trainPredict[:,0]))
    print('Train Score: %.2f RMSE' % (trainRMSE))
    testRMSE = math.sqrt(mean_squared_error(testY[0], testPredict[:,0]))
    print('Test Score: %.2f RMSE' % (testRMSE))
    
    
    mae_from_sklearn = mean_absolute_error(testY[0], testPredict[:,0])
    # rmse_from_sklearn = root_mean_squared_error(testY[0], testPredict[:,0]) 
    r2_from_sklearn = r2_score(testY[0], testPredict[:,0])
    print('MAE Score: %.2f MAE' % (mae_from_sklearn))
    print('R2 Score: %.2f r2' % (r2_from_sklearn))
    
    sum_time = 0
    i = 0
    for val in x_test[0:10]:
        testing_start_time = time.time()
        t = val.reshape(1, 1, loop_back_variable)
        p = model.predict(t)
        testing_time = time.time() - testing_start_time
        sum_time += testing_time
        print('predicted for x_test[{{0}}]: ', i, p)
        i = i+1
    test_time = sum_time/10;
    print('Average predicted time: ', test_time)
    
    
    
    #open the csv file and save result
    all_results = {"valueType":colName, "slidingWind": loop_back_variable, "RMSE_train": trainRMSE,
                   "RMSE":testRMSE, "MAE": mae_from_sklearn, "r2":r2_from_sklearn, 
                   "trainingTime":training_time, "predTime": test_time}
    with open (all_result_file, 'a') as filedata: 
        writer = csv.DictWriter(filedata, delimiter=',', fieldnames=columns_res)
        writer.writerow(all_results)
    
    #------------ plot results ---------------
    # shift train predictions for plotting
    trainPredictPlot = np.empty_like(dataset)
    trainPredictPlot[:, :] = np.nan
    trainPredictPlot[loop_back_variable:len(trainPredict)+loop_back_variable, :] = trainPredict
    # shift test predictions for plotting
    testPredictPlot = np.empty_like(dataset)
    testPredictPlot[:, :] = np.nan
    testPredictPlot[len(trainPredict)+(loop_back_variable*2)+1:len(dataset)-1, :] = testPredict
    
    
    # plot baseline and predictions
    plt.plot(min_max_scaler.inverse_transform(dataset))
    plt.plot(trainPredictPlot)
    plt.plot(testPredictPlot)
    plt.legend(["Train", "Train_Prediction", "Test_prediciton"])
    plt.xlabel('Time (hours)')
    plt.ylabel('Security Posture')
    plt.ylim(0, 1)
    # plt.xticks(data_df['Time'])
    plt.show()
    
    
    
#call for all column
for column in df:
    train_model(df, column)
    print(column, " is completed")