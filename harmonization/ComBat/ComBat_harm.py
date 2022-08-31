#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
Written by Lijun An and CBIG under MIT license:
https://github.com/ThomasYeoLab/CBIG/blob/master/LICENSE.md
'''
import os
import rpy2.robjects as ro
from config import global_config

# set environment variable
os.environ['R_HOME'] = global_config.r_home


def R_caller(working_dir, fold_input_path, fold_output_path, train_val_file,
             test_file, isRef, isSaveTrain):
    """
    Call ComBat R package to perform harmonization for one fold

    Args:
        working_dir (str): Path for working dir
        fold_input_path (str): Path for <fold> input csvs
        fold_output_path (str): Path for saving <fold> output
        train_val_file (str): Name for train+val csv to harmonize
        test_file (str): Name for test csv to harmonize
        isRef (bool): Whether map to ADNI site
        isSaveTrain (bool): Whether saving harmonized training file
    """
    r = ro.r
    r.source(os.path.join(working_dir, 'run_ComBat.R'))
    _ = r['ComBatHarm'](working_dir, fold_input_path, fold_output_path,
                        train_val_file, test_file, isRef, isSaveTrain)


def ComBat_harm(input_path,
                output_path,
                prefix,
                train_val_file,
                test_files,
                isRef,
                nb_folds=10):
    """
    Run ComBat harmonization for <nb_folds> folds

    Args:
        input_path (str): Path for input csvs
        output_path (str): Path for saving output
        prefix (str): Prefix for saving output
        train_val_file (str): Name for train+val csv to harmonize
        test_files (list): List of names for test csvs to harmonize
        isRef (bool): Whether map to ADNI site
        nb_folds (int, optional): Number of folds. Defaults to 10.
    """
    working_dir = os.path.join(global_config.root_path, 'harmonization',
                               'ComBat', 'ComBat_R')
    for fold in range(nb_folds):
        fold_input_path = os.path.join(input_path, str(fold))
        fold_output_path = os.path.join(output_path, str(fold))
        for i, test_file in enumerate(test_files):
            if i == 0:
                R_caller(
                    working_dir,
                    fold_input_path,
                    fold_output_path,
                    prefix + '_' + train_val_file,
                    test_file,
                    isRef,
                    isSaveTrain=1)
            else:
                R_caller(
                    working_dir,
                    fold_input_path,
                    fold_output_path,
                    prefix + '_' + train_val_file,
                    test_file,
                    isRef,
                    isSaveTrain=0)
