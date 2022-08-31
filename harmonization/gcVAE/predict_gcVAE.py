#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
Written by Lijun An and CBIG under MIT license:
https://github.com/ThomasYeoLab/CBIG/blob/master/LICENSE.md
'''
import os
import torch
import argparse
import pandas as pd
import numpy as np
from config import global_config
from utils.nn_misc import vae_harm_predict
from utils.misc import \
    create_folder, load_pkl, txt2list, one_hot, replace_with_harmed_ROI_wrapper


def predict_gcvae_args_parser():
    """
    Parameters for making prediction using trained cVAE model
    """
    parser = argparse.ArgumentParser(prog='PredgcVAEArgs')
    # input and output path
    parser.add_argument('--raw_data_path', type=str, default='/')
    parser.add_argument('--harm_input_path', type=str, default='/')
    parser.add_argument('--checkpoint_path', type=str, default='/')
    parser.add_argument('--harm_output_path', type=str, default='/')
    parser.add_argument('--dataset_pair', type=str, default='ADNI-AIBL')
    parser.add_argument('--exp', type=str, default='unmatch2match')
    parser.add_argument('--nb_pred', type=int, default=100)
    parser.add_argument('--nb_folds', type=int, default=10)
    parser.add_argument(
        '--harm_files', type=list, default=['train', 'val', 'test'])
    parser.add_argument(
        '--origin_files', type=list, default=['train', 'val', 'test'])
    # in case there are unexcepted args
    pred_args, _ = parser.parse_known_args()

    return pred_args


def predict(args):
    """
    Making prediction using trained cVAE model

    Args:
        args (tuple): Parameters
    """
    if args.exp == 'unmatch2match':
        args.harm_files = ['train', 'val', 'unmatch2match_test']
        args.origin_files = [
            'unmatch2match_train', 'unmatch2match_val', 'unmatch2match_test'
        ]
    elif args.exp == 'match2unmatch':
        args.harm_files = ['train', 'val', 'match2unmatch_test']
        args.origin_files = [
            'match2unmatch_train', 'match2unmatch_val', 'match2unmatch_test'
        ]
    else:
        args.harm_files = [
            'train', 'val', 'unmatch2match_test', 'unmatch2match_train_full',
            'unmatch2match_val_full'
        ]
        args.origin_files = [
            'unmatch2match_train', 'unmatch2match_val', 'unmatch2match_test',
            'unmatch2match_train_full', 'unmatch2match_val_full'
        ]
    assert 'train' in args.harm_files, 'train data is missing'
    ROIs = txt2list(global_config.ROI_features_path)
    for fold in range(args.nb_folds):
        fold_data_path = os.path.join(args.harm_input_path, args.dataset_pair,
                                      str(fold))
        fold_checkpoint_path = os.path.join(args.checkpoint_path, 'harm_model',
                                            'gcVAE', args.dataset_pair,
                                            str(fold))
        fold_output_path = os.path.join(args.harm_output_path,
                                        args.dataset_pair, 'gcVAE', str(fold))
        create_folder(fold_output_path)
        # load model
        model = torch.load(
            os.path.join(fold_checkpoint_path, 'gcVAE2.pt'),
            map_location='cpu')
        model.to(torch.device('cpu'))
        model.eval()
        # load training mean and training std
        train_pkl = load_pkl(os.path.join(fold_data_path, 'train.pkl'))
        mean = train_pkl['mean'][ROIs].values
        std = train_pkl['std'][ROIs].values
        for harm_file in args.harm_files:
            harm_pkl = load_pkl(
                os.path.join(fold_data_path, harm_file + '.pkl'))
            roi_array = harm_pkl['data'][ROIs].values
            site_onehot = one_hot(harm_pkl['data']['SITE'].values)
            x = np.concatenate((roi_array, site_onehot), axis=1)
            x = torch.tensor(x).float()
            x_hat = np.zeros_like(roi_array)
            x_hat_map2ADNI = np.zeros_like(roi_array)
            x_hat_intermediate = np.zeros_like(roi_array)
            sites_map2ADNI = torch.tensor(np.zeros_like(site_onehot)).float()
            sites_map2ADNI[:, 0] = 1
            sites_intermediate = torch.tensor(
                np.zeros_like(site_onehot)).float()
            for i in range(args.nb_pred):
                x_hat += \
                    vae_harm_predict(model, x, i+2021) / args.nb_pred
                x_hat_map2ADNI += \
                    vae_harm_predict(
                        model, x, i+2021, sites_map2ADNI) / args.nb_pred
                x_hat_intermediate += \
                    vae_harm_predict(
                        model, x, i+2021, sites_intermediate) / args.nb_pred
            # denormalization
            x_hat_map2ADNI = (x_hat_map2ADNI * std) + mean
            for i in range(mean.shape[0]):
                x_hat_map2ADNI[:, i][x_hat_map2ADNI[:, i] <= 0] = mean[i]
            x_hat_map2ADNI_df = pd.DataFrame(data=x_hat_map2ADNI, columns=ROIs)
            map2ADNI_save_name = 'harm_' + harm_file + '_ROI-map2ADNI.csv'
            x_hat_map2ADNI_df.to_csv(
                os.path.join(fold_output_path, map2ADNI_save_name),
                index=False,
                sep=',')
            x_hat_intermediate = (x_hat_intermediate * std) + mean
            for i in range(mean.shape[0]):
                x_hat_intermediate[:, i][
                    x_hat_intermediate[:, i] <= 0] = mean[i]
            x_hat_intermediate_df = pd.DataFrame(
                data=x_hat_intermediate, columns=ROIs)
            intermediate_save_name = \
                'harm_' + harm_file + '_ROI-intermediate.csv'
            x_hat_intermediate_df.to_csv(
                os.path.join(fold_output_path, intermediate_save_name),
                index=False,
                sep=',')
            x_hat = (x_hat * std) + mean
            for i in range(mean.shape[0]):
                x_hat[:, i][x_hat[:, i] <= 0] = mean[i]
            x_hat_df = pd.DataFrame(data=x_hat, columns=ROIs)
            save_name = 'harm_' + harm_file + '_ROI-recon.csv'
            x_hat_df.to_csv(
                os.path.join(fold_output_path, save_name),
                index=False,
                sep=',')
    # replace by harmonized ROIs
    # reconstruction
    replace_with_harmed_ROI_wrapper(
        os.path.join(args.raw_data_path, args.dataset_pair),
        os.path.join(args.harm_output_path, args.dataset_pair, 'gcVAE'),
        args.origin_files, args.harm_files, args.nb_folds, '-recon')
    # map2ADNI
    replace_with_harmed_ROI_wrapper(
        os.path.join(args.raw_data_path, args.dataset_pair),
        os.path.join(args.harm_output_path, args.dataset_pair, 'gcVAE'),
        args.origin_files, args.harm_files, args.nb_folds, '-map2ADNI')
    # intermediate
    replace_with_harmed_ROI_wrapper(
        os.path.join(args.raw_data_path, args.dataset_pair),
        os.path.join(args.harm_output_path, args.dataset_pair, 'gcVAE'),
        args.origin_files, args.harm_files, args.nb_folds, '-intermediate')


if __name__ == '__main__':
    predict(predict_gcvae_args_parser())
