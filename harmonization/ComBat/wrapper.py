#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
Written by Lijun An and CBIG under MIT license:
https://github.com/ThomasYeoLab/CBIG/blob/master/LICENSE.md
'''
import os
import itertools
import argparse
from typing import List
from harmonization.ComBat.ComBat_preproc import ComBat_preproc
from harmonization.ComBat.ComBat_harm import ComBat_harm
from harmonization.ComBat.ComBat_postproc import ComBat_postproc
from utils.misc import list2str, tuple2str, \
    clean_nfolds_files, create_nfolds_folder


def fit_combat_args_parser():
    """
    Parameters for ComBat harmonization
    """
    parser = argparse.ArgumentParser(prog='ComBatArgs')
    parser.add_argument('--dataset_pair', type=str, default='ADNI-AIBL')
    parser.add_argument('--exp', type=str, default='unmatch2match')
    parser.add_argument('--prefix', type=str, default='unmatch2match')
    parser.add_argument('--data_path', type=str, default='/')
    parser.add_argument('--output_path', type=str, default='/')
    parser.add_argument(
        '--COVs', type=List, default=['AGE', 'SEX', 'MMSE', 'DX'])
    parser.add_argument('--isRef', type=int, default=1)
    parser.add_argument('--nb_folds', type=int, default=10)
    parser.add_argument('--train_file', type=str, default='train')
    parser.add_argument('--val_file', type=str, default='val')
    parser.add_argument('--train_val_file', type=str, default='train_val')
    parser.add_argument('--test_files', type=List, default=['test'])
    combat_args, _ = parser.parse_known_args()

    return combat_args


def ComBat(args):
    """
    Run ComBat harmonization

    Args:
        args (tuple): Parameters
    """
    covs_folder = list2str(args.COVs)
    if args.isRef == 0:
        covs_folder += '_noref'
    data_path = args.data_path
    harm_output_path = os.path.join(args.output_path, covs_folder)
    # 1. create sub folders for saving output files
    create_nfolds_folder(harm_output_path, args.nb_folds, isOverwrite=True)
    # 2. ComBat preprocess
    ComBat_preproc(data_path, harm_output_path, args.COVs, args.prefix,
                   args.train_file, args.val_file, args.test_files,
                   args.nb_folds)
    # 3. ComBat harmonization
    ComBat_harm(harm_output_path, harm_output_path, args.prefix,
                args.train_val_file, args.test_files, args.isRef,
                args.nb_folds)
    # 4. ComBat postprocess
    harm_files = [args.prefix + '_' + args.train_val_file] + args.test_files
    harm_files2 = ['harm_' + args.prefix + '_' + args.train_val_file + '_ROI'
                   ] + ['harm_' + f + '_ROI' for f in args.test_files]
    ComBat_postproc(data_path, harm_output_path, harm_files2, args.nb_folds)
    # 5. clean intermediate files
    input_suffixs = ['ROI.csv', 'site.csv', 'covariates.csv']
    intermdiate_files = \
        [tuple2str(f) for f in itertools.product(harm_files, input_suffixs)]
    intermdiate_files += harm_files2
    clean_nfolds_files(harm_output_path, intermdiate_files, args.nb_folds)


def ComBat_wrapper(args):
    """
    Wrapper function for running ComBat harmonization
    run for two covariates sets & two ways (map to ADNI or intermediate space)

    Args:
        args (tuple): Parameters
    """
    # set test_files
    if args.exp == 'unmatch2match':
        args.test_files = ['unmatch2match_test']
    elif args.exp == 'match2unmatch':
        args.test_files = ['match2unmatch_test']
    else:
        args.test_files = [
            "unmatch2match_test", "unmatch2match_train_full",
            "unmatch2match_val_full"
        ]
    if args.exp == 'match2unmatch':
        args.prefix = 'match2unmatch'
    else:
        args.prefix = 'unmatch2match'
    # AGE-SEX-MMSE_DX
    args.COVs = ['AGE', 'SEX', 'MMSE', 'DX']
    args.isRef = 0
    ComBat(args)
    args.isRef = 1
    ComBat(args)
    # AGE-SEX
    args.COVs = ['AGE', 'SEX']
    args.isRef = 0
    ComBat(args)
    args.isRef = 1
    ComBat(args)


if __name__ == '__main__':
    ComBat_wrapper(fit_combat_args_parser())
