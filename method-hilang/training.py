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
from util_method import save_model, load_model, plot_pred_against, plot_pred_comparison, standardize
### to edit accordingly.
# from dataloader import dataset_ave_no_profile as dataset_class
from dataloader import rdm_dataset as dataset_class
### to edit accordingly.
from network import Three_FC_layer as archi

#####################
####    Train    ####
#####################
def train(train_loader, model, valid_loader, args):
    loss_log = {
        'train_mse' : [],
        'train_r' : [],
        'valid_mse' : [],
        'valid_r' : []
    }
    '''
        intial round
    '''
    with torch.no_grad():
        epoch_loss_log = {
            'mse' : [],
            'r' : []
        }
        for batchidx, (feature, label) in enumerate(train_loader):
            numbatches = len(train_loader)
            # Transfer to GPU
            feature, label = feature.to(device).float(), label.to(device).float()
            # clear gradients 
            optimizer.zero_grad()
            # forward pass
            output = model.forward(feature)
            # MSE Loss calculation
            loss_mse = nn.MSELoss()(output.squeeze(), label.squeeze())
            loss_r = pearson_corr_loss(output.squeeze(), label.squeeze())

            epoch_loss_log['mse'].append(loss_mse.item())
            epoch_loss_log['r'].append(loss_r.item())
        
        aveloss_mse = np.average(epoch_loss_log['mse'])
        aveloss_r = np.average(epoch_loss_log['r'])
        print(f'Initial round without training || mse = {aveloss_mse:.2f} || r = {aveloss_r:.2f}')
        loss_log['train_mse'].append(aveloss_mse)
        loss_log['train_r'].append(aveloss_r)
    
    '''
        actual training
    '''
    n_epochs_least = 100
    n_epochs_stop = 50
    epochs_no_improve = 0
    min_val_loss = np.Inf
    early_stop = False

    for epoch in np.arange(args.num_epochs):
        # val_loss = 0 # for early stopping
        model.train()
        start_time = time.time()
        epoch_loss_log = {
            'mse' : [],
            'r' : []
        }

        for batchidx, (feature, label) in enumerate(train_loader):
            
            numbatches = len(train_loader)
            # Transfer to GPU
            feature, label = feature.to(device).float(), label.to(device).float()
            # clear gradients 
            optimizer.zero_grad()
            # forward pass
            output = model.forward(feature)

            # loss
            loss_mse = nn.MSELoss()(output.squeeze(), label.squeeze())
            loss_r = pearson_corr_loss(output.squeeze(), label.squeeze())
            loss = loss_mse*args.mse_weight + loss_r

            # backward pass
            loss.backward(retain_graph=True)
            # update parameters
            optimizer.step()

            # record training loss
            epoch_loss_log['mse'].append(loss_mse.item())
            epoch_loss_log['r'].append(loss_r.item())

            print(f'Epoch: {epoch} || Batch: {batchidx}/{numbatches} || mse = {loss_mse.item():5f} || r = {loss_r.item():5f}', end = '\r')

            # val_loss += loss.item()
        
        
        # log average loss
        aveloss_mse = np.average(epoch_loss_log['mse'])
        aveloss_r = np.average(epoch_loss_log['r'])
        # print(f'Initial round without training || mse = {aveloss_mse:.2f} || r = {aveloss_r:.2f}')
        loss_log['train_mse'].append(aveloss_mse)
        loss_log['train_r'].append(aveloss_r)
        print(' '*200)

        epoch_duration = time.time() - start_time
        print(f'Epoch: {epoch:3} || mse: {aveloss_mse:8.5f} || r: {aveloss_r:8.5f} || time taken (s): {epoch_duration:8f}')
        
        # test_ave_mse, test_ave_r  = test(model, test_loader)
        valid_ave_mse, valid_ave_r, valid_loss  = test(model, valid_loader)

        # loss_log['test_mse'].append(test_ave_mse)
        # loss_log['test_r'].append(test_ave_r)
        loss_log['valid_mse'].append(valid_ave_mse)
        loss_log['valid_r'].append(valid_ave_r)
        
        # val_loss = val_loss / len(train_loader)
        # print(sum_test, min_val_loss)
        if valid_loss < min_val_loss:
            # print('meow')
            epochs_no_improve = 0
            min_val_loss = valid_loss
            best_epoch = epoch
            best_model = model
            best_valid_ave_mse = valid_ave_mse
            best_valid_ave_r = valid_ave_r

        else:
            epochs_no_improve += 1
        print(epochs_no_improve)
        # iter += 1
        if epoch > n_epochs_least and epochs_no_improve == n_epochs_stop:
            print('Early stopping!' )
            early_stop = True
        
        if early_stop:
            print("Stopped")
            break
    

    # plot loss against epochs
    plt.plot(loss_log['train_mse'][1::], label='training loss mse')
    plt.plot(loss_log['valid_mse'], label='validation loss mse')
    plt.plot(loss_log['train_r'][1::], label='training loss r')
    plt.plot(loss_log['valid_r'], label='validation loss r')
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.ylim([-1, 1])
    plt.legend()
    plt.title(f"Loss || init mse:{loss_log['train_mse'][0]:.3f} | r:{loss_log['train_r'][0]:.3f} || valid mse: {best_valid_ave_mse:.3f} | r: {best_valid_ave_r:.3f}")
    plt.savefig(os.path.join(args.dir_path, 'saved_models', f'{args.model_name}', 'loss_plot.png'))
    plt.close()

    return best_model, best_valid_ave_mse, best_valid_ave_r, best_epoch
    # return model, test_ave_mse, test_ave_r

####################
####    Test    ####
####################

def test(model, test_loader):
    # print('test?')

    model.eval()

    epoch_loss_log = {
            'mse' : [],
            'r' : []
        }
    with torch.no_grad():
        # model = load_model(model_name)
        for batchidx, (feature, label) in enumerate(test_loader):
            # print('feature: ', feature)
            
            feature, label = feature.to(device).float(), label.to(device).float()
            # forward pass
            output = model(feature)
            # MSE Loss calculation
            # print('output: ', output, 'label: ', label)

            loss_mse = nn.MSELoss()(output.squeeze(), label.squeeze())
            loss_r = pearson_corr_loss(output.squeeze(), label.squeeze())
            # loss = loss_mse + loss_r
            # print(loss)
            epoch_loss_log['mse'].append(loss_mse.item())
            epoch_loss_log['r'].append(loss_r.item())
    
    test_ave_mse = np.average(epoch_loss_log['mse'])
    test_ave_r = np.average(epoch_loss_log['r'])
    sum_test = test_ave_mse + test_ave_r
    print(f'average test lost (per batch): mse: {test_ave_mse:4f} r: {test_ave_r:4f}')
    return test_ave_mse, test_ave_r, sum_test


def single_test(model, songurl, exps, args):

    # features - audio
    testfeat = test_feat_dict[songurl]
    # labels
    testlabel = exps.at[songurl,'labels']

    testinput = testfeat

    with torch.no_grad():
        testinput = torch.from_numpy(testinput)
        testlabel = torch.from_numpy(testlabel)

        feature, label = testinput.to(device).float(), testlabel.to(device).float()
        # model = load_model(model, args.model_name, args.dir_path)

        # forward pass
        output = model(feature)
        # print(testinput.shape)
        # print(output.shape)
        # print(testlabel.shape)
        # MSE Loss calculation
        # loss = criterion(output.squeeze(), label.squeeze())
        loss_mse = nn.MSELoss()(output.squeeze(), label.squeeze())
        loss_r = pearson_corr_loss(output.squeeze(), label.squeeze())
        # loss = loss_mse + loss_r
    # print(loss.item())

    dir_path = os.path.dirname(os.path.realpath(__file__))

    plt = plot_pred_comparison(output, label, loss_mse.item(), loss_r.item())
    plt.suptitle(f'{songurl}')
    plt.savefig(os.path.join(dir_path, 'saved_models', f'{args.model_name}/predictions/{songurl}_prediction.png'))
    plt.close()

    plt = plot_pred_against(output, label)
    plt.suptitle(f'{songurl}')
    plt.savefig(os.path.join(dir_path, 'saved_models', f'{args.model_name}/predictions/{songurl}_y_vs_yhat.png'))
    plt.close()

####################
####    Misc    ####
####################

def dataloader_prep(feat_dict, exps, args, train=True):
    params = {'batch_size': args.batch_size,
        'shuffle': True,
        'num_workers': args.num_workers}
    # prepare data for testing
    dataset_obj = dataset_class(feat_dict, exps, train)
    # dataset = dataset_obj.gen_dataset()#train=train)
    loader = DataLoader(dataset_obj, **params)

    return loader

if __name__ == "__main__":
    
    ########################
    ####    Argparse    ####
    ########################

    dir_path = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument('--dir_path', type=str, default=dir_path)
    parser.add_argument('--affect_type', type=str, default='arousals', help='Can be either "arousals" or "valences"')
    parser.add_argument('--num_epochs', type=int, default=300)
    parser.add_argument('--model_name', type=str, default='mse10', help='Name of folder plots and model will be saved in')
    parser.add_argument('--batch_size', type=int, default=8)
    parser.add_argument('--num_workers', type=int, default=10)
    parser.add_argument('--hidden_dim', type=int, default=512)
    # parser.add_argument('--lstm_size', type=int, default=10)
    # parser.add_argument('--step_size', type=int, default=5)
    parser.add_argument('--mse_weight', type=float, default=10.0)
    parser.add_argument('--learning_rate', type=float, default=0.0001)
    # parser.add_argument('--conditions', nargs='+', type=str, default=[])

    args = parser.parse_args()
    setattr(args, 'model_name', f'{args.affect_type[0]}_np_{args.model_name}')
    print(args)

    # check if folder with same model_name exists. if not, create folder.
    os.makedirs(os.path.join(dir_path,'saved_models', args.model_name), exist_ok=True)
    os.makedirs(os.path.join(dir_path,'saved_models', args.model_name, 'predictions'), exist_ok=True)

    #########################
    ####    Load Data    ####
    #########################

    # load the data 
    # read audio features from pickle
    train_feat_dict = util.load_pickle('data/train_feats.pkl')
    valid_feat_dict = util.load_pickle('data/valid_feats.pkl')
    test_feat_dict = util.load_pickle('data/test_feats.pkl')
    # read labels from pickle
    exps = pd.read_pickle(f'data/exps_std_{args.affect_type[0]}_ave3.pkl')
    # original_exps = pd.read_pickle('data/exps_ready.pkl')
    
    ####################
    ####    Cuda    ####
    ####################

    # CUDA for PyTorch
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda:0" if use_cuda else "cpu")
    torch.manual_seed(42)
    torch.backends.cudnn.benchmark = True
    print('cuda: ', use_cuda)
    print('device: ', device)

    ####################
    ####    Loss    ####
    ####################

    def pearson_corr_loss(output, target):
        x = output
        y = target

        vx = x - torch.mean(x)
        vy = y - torch.mean(y)

        cost = torch.sum(vx * vy) / (torch.sqrt(torch.sum(vx ** 2)) * torch.sqrt(torch.sum(vy ** 2)))
        if torch.isnan(cost):
            return torch.tensor([0]).to(device)
        else:
            return cost*-1

    # def weighted_mse_loss(output, target):
    #     mseloss = nn.MSELoss()(output, target)
        
    #     return args.mse_weight * mseloss # does this work??

    ###########################
    ####    Model param    ####
    ###########################

    ## MODEL
    input_dim = list(train_feat_dict.values())[0].shape[1] #724 # 1582 
    print('check input_dim: ', input_dim)
    model = archi(input_dim=input_dim, reduced_dim=args.hidden_dim, fc_dim=64).to(device)
    model.float()
    print(model)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    ########################
    ####    Training    ####
    ########################
     
    train_loader = dataloader_prep(train_feat_dict, exps, args)
    valid_loader = dataloader_prep(valid_feat_dict, exps, args)
    test_loader = dataloader_prep(test_feat_dict, exps, args)
    
    ## model, test_ave_mse, test_ave_r = train(train_loader, model, test_loader, args)
    model, val_ave_mse, val_ave_r, num_epochs = train(train_loader, model, valid_loader, args)
    save_model(model, args.model_name, dir_path)

    #######################
    ####    Testing    ####
    #######################

    # model = archi(input_dim=input_dim, reduced_dim=args.hidden_dim, fc_dim=64).to(device)
    # model = load_model(model, args.model_name, dir_path)
    test_ave_mse, test_ave_r, sum_test  = test(model, test_loader)

    for songurl in util.testlist:
        single_test(model, songurl, exps, args)

    # logging

    args_dict = vars(args)
    # print(type(args_dict))
    args_dict['num_epochs'] = num_epochs
    args_dict['v_mse'] = f'{val_ave_mse:.6f}'
    args_dict['v_r'] = f'{val_ave_r:.6f}'
    args_dict['v_loss'] = f'{val_ave_mse+val_ave_r:.6f}'

    args_dict['t_mse'] = f'{test_ave_mse:.6f}'
    args_dict['t_r'] = f'{test_ave_r:.6f}'
    args_dict['t_loss'] = f'{sum_test:.6f}'
    args_dict.pop('dir_path')
    # print(args_dict)
    args_series = pd.Series(args_dict)
    args_df = args_series.to_frame().transpose()
    # print(args_df)

    exp_log_filepath = os.path.join(dir_path,'saved_models','experiment_log2.pkl')
    if os.path.exists(exp_log_filepath):
        exp_log = pd.read_pickle(exp_log_filepath)
        exp_log = exp_log.append(args_df).reset_index(drop=True)
        pd.to_pickle(exp_log, exp_log_filepath)
        print(exp_log)
    else:
        pd.to_pickle(args_df, exp_log_filepath)
        print(args_df)