import os
import sys
# sys.path.append(os.path.abspath('../..'))
sys.path.append(os.path.abspath(''))
print(sys.path)

import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time


import torch
from torch import optim, nn
from torch.utils.data import DataLoader

import util
### to edit accordingly.
from dataloader import dataset_non_ave_with_profile as dataset_class
### to edit accordingly.
from network import Two_FC_layer as archi


# CUDA for PyTorch
use_cuda = torch.cuda.is_available()
device = torch.device("cuda:0" if use_cuda else "cpu")
torch.manual_seed(42)
torch.backends.cudnn.benchmark = True
print('cuda: ', use_cuda)
print('device: ', device)

# Parameters
affect_type = 'arousals'
params = {'batch_size': 128,
          'shuffle': True,
          'num_workers': 6}
max_epochs = 100
possible_conditions = np.array(['age', 'country_enculturation', 'country_live', 'fav_music_lang', 'gender', 'fav_genre', 'play_instrument', 'training', 'training_duration'])
# conditions = ['play_instrument']
conditions = possible_conditions


'''
load data
'''
feat_dict = util.load_pickle('data/feat_dict_ready.pkl')
exps = pd.read_pickle(os.path.join('data', 'exps_ready.pkl'))
pinfo = pd.read_pickle(os.path.join('data', 'pinfo_numero.pkl'))



## MODEL
input_dim = 1582 + len(conditions)
model = archi(input_dim=input_dim).to(device)
model.float()
print(model)
model.train()

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

def train(train_loader):
    loss_epoch_log = []

    # one round without training.
    loss_log = []
    for batchidx, (feature, label) in enumerate(train_loader):
        numbatches = len(train_loader)
        # Transfer to GPU
        feature, label = feature.to(device).float(), label.to(device).float()
        # clear gradients 
        optimizer.zero_grad()
        # forward pass
        output = model.forward(feature)
        # MSE Loss calculation
        loss = criterion(output.squeeze(), label.squeeze())
        loss_log.append(loss.item())
    aveloss = np.average(loss_log)
    loss_epoch_log.append(aveloss)
    print(f'Initial round without training || MSELoss = {aveloss:.6f}')

    for epoch in np.arange(1, max_epochs+1):
        start_time = time.time()
        loss_log = []

        # Training
        for batchidx, (feature, label) in enumerate(train_loader):
            numbatches = len(train_loader)
            # Transfer to GPU
            feature, label = feature.to(device).float(), label.to(device).float()
            # clear gradients 
            optimizer.zero_grad()
            # forward pass
            output = model.forward(feature)
            # MSE Loss calculation
            loss = criterion(output.squeeze(), label.squeeze())
            # backward pass
            loss.backward(retain_graph=True)
            # update parameters
            optimizer.step()
            # record training loss
            loss_log.append(loss.item())
            print(f'Epoch: {epoch} || Batch: {batchidx}/{numbatches} || MSELoss = {loss.item()}', end = '\r')
            
        aveloss = np.average(loss_log)
        print(' '*200)
        loss_epoch_log.append(aveloss)

        epoch_duration = time.time() - start_time
        print(f'Epoch: {epoch:3} || MSELoss: {aveloss:10.6f} || time taken (s): {epoch_duration}')


    # plot loss against epochs
    plt.plot(loss_epoch_log[1::])
    plt.xlabel('epoch')
    plt.ylabel('mseloss')
    plt.title(f'Training loss (before training: {loss_epoch_log[0]:.6f})')
    dir_path = os.path.dirname(os.path.realpath(__file__))
    plt.savefig(os.path.join(dir_path, 'saved_models', f'{model_name}_loss_plot.png'))
    
    plt.close()

    return model

def save_model(model, model_name):

    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_to_save = os.path.join(dir_path, 'saved_models', f"{model_name}.pth")
    torch.save(model.state_dict(), path_to_save)
    # loss_fig.savefig(os.path.join(args.model_path, f"{model_name}_loss_plot.png"))

def load_model(model_name):

    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_to_load = os.path.join(dir_path, 'saved_models', f"{model_name}.pth")
    model.load_state_dict(torch.load(path_to_load))
    model.eval() # assuming loading for eval and not further training. (does not save optimizer so shouldn't continue training.)
    return model

def run_training(model_name):

    # prepare data for training
    dataset_obj = dataset_class(affect_type, feat_dict, exps, pinfo, conditions)
    train_dataset = dataset_obj.gen_dataset(train=True)
    train_loader = DataLoader(train_dataset, **params)

    # train.
    model = train(train_loader)
    save_model(model, model_name)
    single_test(model_name)

def plot_pred_comparison(output, label, mseloss):
    plt.plot(output.cpu().numpy(), label='pred')
    plt.plot(label.cpu().numpy(), label='ori')
    plt.legend()
    plt.xlabel('Time')
    plt.ylabel(f'{affect_type}')
    plt.title(f'Prediction vs Ground Truth || mse: {mseloss}')
    return plt

def plot_pred_against(output, label, mseloss):
    actual = label.cpu().numpy()
    predicted = output.squeeze().cpu().numpy()
    plt.scatter(actual, predicted)
    plt.xlabel('ground truth')
    plt.ylabel('prediction')
    plt.title(f'Prediction against Ground Truth || mse: {mseloss}')
    return plt

# plot prediction of one song.
# feat_dict['']

'''
testing
'''
def single_test(model_name):
    # features - audio
    testfeat = feat_dict['01_139']
    # features - pinfo
    testtrial = exps[exps['songurl']=='01_139'].reset_index().loc[0]
    testwid = testtrial['workerid']
    single_pinfo_df = pinfo[pinfo['workerid'] == testwid]
    single_pinfo_df = single_pinfo_df[conditions]
    testpinfo = single_pinfo_df.values.tolist()[0]
    # labels
    testlabel = testtrial[affect_type]

    testinput = np.array([list(audiofeat) + list(testpinfo) for audiofeat in testfeat])

    with torch.no_grad():
        testinput = torch.from_numpy(testinput)
        testlabel = torch.from_numpy(testlabel)

        feature, label = testinput.to(device).float(), testlabel.to(device).float()
        model = load_model(model_name)

        # forward pass
        output = model(feature)
        # MSE Loss calculation
        loss = criterion(output.squeeze(), label.squeeze())
    # print(loss.item())

    dir_path = os.path.dirname(os.path.realpath(__file__))

    plt = plot_pred_comparison(output, label, loss.item())
    plt.savefig(os.path.join(dir_path, 'saved_models', f'{model_name}_prediction.png'))
    plt.close()

    plt = plot_pred_against(output, label, loss.item())
    plt.savefig(os.path.join(dir_path, 'saved_models', f'{model_name}_y_vs_yhat.png.png'))
    plt.close()

def test(model_name):
    # prepare data for testing
    dataset_obj = dataset_class(affect_type, feat_dict, exps, pinfo, conditions)
    test_dataset = dataset_obj.gen_dataset(train=False)
    test_loader = DataLoader(test_dataset, **params)

    loss_log = []
    with torch.no_grad():
        model = load_model(model_name)
        for batchidx, (feature, label) in enumerate(test_loader):
            
            feature, label = feature.to(device).float(), label.to(device).float()
            # forward pass
            output = model(feature)
            # MSE Loss calculation
            loss = criterion(output.squeeze(), label.squeeze())
            # print(loss)
            loss_log.append(loss.item())
    aveloss = np.average(loss_log)
    print(f'average test lost (per batch): {aveloss}')

model_name = 'test3'
# run_training(model_name)
single_test(model_name)
# test(model_name)