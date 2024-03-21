import os
import sys
import time
import json
import glob
import boto3
import joblib
import logging
import argparse
import botocore
import functools
import subprocess
import multiprocessing

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score, 
    roc_auc_score,
    accuracy_score
)

from datetime import datetime
from pathlib import Path
from pprint import pprint



#########################################################################
############################ Parse arguments ############################
def parse_args():
    parser = argparse.ArgumentParser(description='Process')
    
    # ====================== Model hyperparameters =====================    
    parser.add_argument('--n_estimators', type=int,
        default=200
    )
    
    parser.add_argument('--max_depth', type=int,
        default=3
    )
    
    parser.add_argument('--criterion', type=str,
        default='gini'
    )
    
    parser.add_argument('--random_state', type=int,
        default=2024
    )
    
    # ====================== Container environment =====================
    parser.add_argument('--hosts', 
                        type=list, 
                        default=json.loads(os.environ['SM_HOSTS']))
    
    parser.add_argument('--current_host', 
                        type=str, 
                        default=os.environ['SM_CURRENT_HOST'])
    
    parser.add_argument('--model_dir', 
                        type=str, 
                        default=os.environ['SM_MODEL_DIR'])

    parser.add_argument('--train_data', 
                        type=str, 
                        default=os.environ['SM_CHANNEL_TRAIN'])
    
    parser.add_argument('--validation_data', 
                        type=str, 
                        default=os.environ['SM_CHANNEL_VALIDATION'])
        
    parser.add_argument('--output_dir', 
                        type=str, 
                        default=os.environ['SM_OUTPUT_DIR'])
    
    parser.add_argument('--num_gpus', 
                        type=int, 
                        default=os.environ['SM_NUM_GPUS'])
    
    # ======================= Debugger arguments ======================
    
    return parser.parse_args()




########################################################################
############################# Data loader ##############################
def load_data(path):
    input_files = glob.glob('{}/*.csv'.format(path))[0]
    print('Importing {}'.format(input_files))
    data = pd.read_csv(path)
    
    data.drop(columns=data.columns[1], inplace=True)
    print('Data import complete.')
    return data



########################################################################
########################### Models training ############################
def model_training(df_train, df_val, n_estimators, max_depth, criterion, random_state, model_dir):
    
    # ================== Retrieve features & targets ================
    print('Retrieving features and targets.')
    train_label = df_train.columns[0]
    
    X_train = df_train.drop(columns=[train_label])
    y_train = df_train[train_label]
    
    X_val = df_val.drop(columns=[train_label])
    y_train = df_val[train_label]
    
    
    # ================== Instanciate and fit models =================
    print('Fitting model...')
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        criterion=criterion,
        random_state=random_state
    )
    
    clf.fit(X_train, y_train)
    print('Model Fitted.')
    
    
    # ================== Compute validation scores =================
    y_pred = clf.predict(X_val)
    proba_pred = clf.predict_proba(X_val)
    
    precision = precision_score(y_val, y_pred)
    recall = recall_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred)
    roc_auc = roc_auc_score(y_val, proba_pred)
    accuracy = accuracy_score(y_val, y_pred)
    
    print('val_precision: {0:.2f}'.format(precision))
    print('val_recall: {1:.2f}'.format(recall))
    print('val_f1score: {2:.2f}'.format(f1))
    print('val_roc_auc: {3:.2f}'.format(roc_auc))
    print('val_accuracy: {4:.2f}%'.format(accuracy))
    
    
    # ========================= Save Models ========================
    path = os.path.join(model_dir, "churn_random_forest.joblib".format(churn_month))
    joblib.dump(clf, path)
    print('Model persisted at ' + model_dir)
    
    
    return clf
    
    
          
    
if name == '__main__':
    
    # Argument parser
    args = parse_args()
    
    
    # Data loading
    train_data = load_data(args.train_data)
    validation_data = load_data(args.validation_data)
    
    
    # Model training
    estimator = model_training(df_train=train_data, 
                               df_val=validation_data, 
                               n_estimators=args.n_estimators, 
                               max_depth=args.max_depth, 
                               criterion=args.criterion, 
                               random_state=args.random_state, 
                               model_dir=args.model_dir)
    
    
    # Prepare for inference which will be used in deployment
    # You will need three files for it: inference.py, requirements.txt, config.json
    inference_path = os.path.join(args.model_dir, "code/")
    os.makedirs(inference_path, exist_ok=True)
    os.system("cp inference.py {}".format(inference_path))
    os.system("cp requirements.txt {}".format(inference_path))
    os.system("cp config.json {}".format(inference_path))