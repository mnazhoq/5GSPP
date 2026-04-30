# -*- coding: utf-8 -*-
"""
Created on Thu Mar 23 23:38:21 2023

@author: umroot
"""

import os
import datetime

import IPython
import IPython.display
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf

mpl.rcParams['figure.figsize'] = (8, 6)
mpl.rcParams['axes.grid'] = False

data_path = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\My Implementation Resources\\synthetic_result_data_with_features.csv"   

data_df  = pd.read_csv(data_path)
print(data_df.head())

date_time = pd.to_datetime(data_df.pop('Time'), format='%Y-%m-%d') #drop the time column
timestamp_s = date_time.map(pd.Timestamp.timestamp) #converting it to seconds
print(timestamp_s[0])


# posture over time
# fft = tf.signal.rfft(data_df['posture_value_goal_node'])
# f_per_dataset = np.arange(0, len(fft))

# n_samples_h = len(data_df['posture_value_goal_node'])
# hours_per_year = 24*365.2524
# years_per_dataset = n_samples_h/(hours_per_year)

# f_per_year = f_per_dataset/years_per_dataset
# plt.step(f_per_year, np.abs(fft))
# plt.xscale('log')
# plt.ylim(0, 400000)
# plt.xlim([0.1, max(plt.xlim())])
# plt.xticks([1, 365.2524], labels=['1/Year', '1/day'])
# _ = plt.xlabel('Frequency (log scale)')

#=============== SPlit the data ==============
column_indices = {name: i for i, name in enumerate(data_df.columns)}

n = len(data_df)
train_df = data_df[0:int(n*0.7)]
val_df = data_df[int(n*0.7):int(n*0.9)]
test_df = data_df[int(n*0.9):]

num_features = data_df.shape[1]


# ============== Normalize the data ============
train_mean = train_df.mean()
train_std = train_df.std()

train_df = (train_df - train_mean) / train_std
val_df = (val_df - train_mean) / train_std
test_df = (test_df - train_mean) / train_std


df_std = (data_df - train_mean) / train_std
df_std = df_std.melt(var_name='Column', value_name='Normalized')
plt.figure(figsize=(12, 6))
ax = sns.violinplot(x='Column', y='Normalized', data=df_std)
_ = ax.set_xticklabels(data_df.keys(), rotation=90)


# ================ Data windowing =======================

class WindowGenerator():
  def __init__(self, input_width, label_width, shift,
               train_df=train_df, val_df=val_df, test_df=test_df,
               label_columns=None):
    # Store the raw data.
    self.train_df = train_df
    self.val_df = val_df
    self.test_df = test_df

    # Work out the label column indices.
    self.label_columns = label_columns
    if label_columns is not None:
      self.label_columns_indices = {name: i for i, name in
                                    enumerate(label_columns)}
    self.column_indices = {name: i for i, name in
                           enumerate(train_df.columns)}

    # Work out the window parameters.
    self.input_width = input_width
    self.label_width = label_width
    self.shift = shift

    self.total_window_size = input_width + shift

    self.input_slice = slice(0, input_width)
    self.input_indices = np.arange(self.total_window_size)[self.input_slice]

    self.label_start = self.total_window_size - self.label_width
    self.labels_slice = slice(self.label_start, None)
    self.label_indices = np.arange(self.total_window_size)[self.labels_slice]

  def __repr__(self):
    return '\n'.join([
        f'Total window size: {self.total_window_size}',
        f'Input indices: {self.input_indices}',
        f'Label indices: {self.label_indices}',
        f'Label column name(s): {self.label_columns}'])

w1 = WindowGenerator(input_width=3, label_width=1, shift=1,
                     label_columns=['posture_value_goal_node'])


print(w1)


# ==================== split_window method will convert them to a window of inputs and a window of labels. ===========

def split_window(self, features):
  inputs = features[:, self.input_slice, :]
  labels = features[:, self.labels_slice, :]
  if self.label_columns is not None:
    labels = tf.stack(
        [labels[:, :, self.column_indices[name]] for name in self.label_columns],
        axis=-1)

  # Slicing doesn't preserve static shape information, so set the shapes
  # manually. This way the `tf.data.Datasets` are easier to inspect.
  inputs.set_shape([None, self.input_width, None])
  labels.set_shape([None, self.label_width, None])

  return inputs, labels

WindowGenerator.split_window = split_window

# Stack three slices, the length of the total window.
# example_window = tf.stack([np.array(train_df[:w1.total_window_size]),
#                            np.array(train_df[100:100+w1.total_window_size]),
#                            np.array(train_df[200:200+w1.total_window_size])])

# example_inputs, example_labels = w1.split_window(example_window)

# print('All shapes are: (batch, time, features)')
# print(f'Window shape: {example_window.shape}')
# print(f'Inputs shape: {example_inputs.shape}')
# print(f'Labels shape: {example_labels.shape}')

