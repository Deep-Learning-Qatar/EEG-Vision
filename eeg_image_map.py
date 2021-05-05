# -*- coding: utf-8 -*-
"""Mapping_Net.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ESLUiFITqGcI8H0XXOkt9FMaqzZ_Jlvd

# **Connect to drive and set-up other stuff**
"""


"""# **Import required Libraries**"""

import os
import time
import torch
import numpy as np
import torch.nn as nn
from torch.utils import data
import matplotlib.pyplot as plt
from torch.nn.utils.rnn import pad_sequence, pack_padded_sequence, pad_packed_sequence


"""# **MyDataset Class**"""

class MyDataset(data.Dataset):

    def __init__(self, X_path, Y_path):
        self.X = np.load(X_path, allow_pickle=True)
        self.Y = np.load(Y_path, allow_pickle=True)

        # Total number of frames
        self.length = self.Y.shape[0]

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        d = torch.as_tensor(self.X[index]).float()
        l = torch.as_tensor(self.Y[index]).long()
        return d, l
    
    def collate(self, batch):
        # Seperate data and labels
        X = [x[0] for x in batch]
        Y = [y[1] for y in batch]

        # Get lengths 
        X_length = torch.as_tensor([len(i) for i in X]).long()
        Y_length = torch.as_tensor([len(j) for j in Y]).long()

        # X_length and Y_length are of equal lengthes (B x T x *)

        return pad_X, pad_Y, X_length, Y_length

class MyDataset_test(data.Dataset):
    def __init__(self, X_path):
        self.X = np.load(X_path, allow_pickle=True)
        
        # Total number of frames
        self.length = self.X.shape[0]
        
    def __len__(self):
        return self.length
    
    def __getitem__(self, index):
        d = torch.as_tensor(self.X[index]).float()
        return d

"""# **Architecture of Bi-LSTM**"""

# There is a lot of exprimental additions here (BN, dropout, type of embiddings layers, ...) 

class BiLSTM(nn.Module):
    def __init__(self, embiddings_num, hidden_size, num_classes, n_layers, bidirectional, dropout):
        super().__init__()
        
        # sequence input layer
        layers1 = []
        layers1.append(nn.Conv1d(embiddings_num, hidden_size, 3, padding=1, bias=False))
        layers1.append(nn.BatchNorm1d(hidden_size))
        layers1.append(nn.ReLU(inplace=True))
        self.embid = nn.Sequential(*layers1)

        # Stacked BiLSTM netwrok
        self.lstm = nn.LSTM(hidden_size,
                            hidden_size,
                            num_layers=n_layers,
                            bidirectional=bidirectional,
                            batch_first=True,
                            dropout=dropout,
                            bias=True)

        # Fully connected layer
        self.fc = nn.Sequential(nn.Linear(hidden_size * 2, hidden_size),
                                nn.Linear(hidden_size, num_classes),
                                nn.Linear(hidden_size, num_classes))


    def forward(self, x): 
        # X: (B x T x *)
        
        # preprocessing to pass it to CNN (B x * x T)
        x2 = x.permute(0, 2, 1)                               # (B x * x T)

        # Through CNN
        embedded = self.embid(x2)                             # (B x * x T)

        # Through BiLSTM
        x3 = embedded.permute(0, 2, 1)                        # (B x T x *)
        output, (hidden, cell) = self.lstm(embedded)          # (B x T x *)

        #classify and apply softmax
        features_out = self.fc(output)                        # (B x T x *)
        
        # class_out = features_out.log_softmax(2)             # (B x T x *) 

        return features_out.permute(1, 0, 2)                  # (T X B x *)


"""# Module functions """
def make_EEG_Image_data_loaders(config):

    # Training Data Loader
    train_dataset = MyDataset(config.train_data_path, config.train_labels_path)
    train_loader_args = dict(shuffle=True, batch_size=config.batch_size, num_workers=4, collate_fn=train_dataset.collate) 
    train_loader = data.DataLoader(train_dataset, **train_loader_args)

    # Validation Data Loader
    val_dataset = MyDataset(config.val_data_path, config.val_labels_path)
    val_loader_args = dict(shuffle=False, batch_size=config.atch_size, num_workers=4, collate_fn=val_dataset.collate)
    val_loader = data.DataLoader(val_dataset, **val_loader_args)

    # Testing Data Loader
    test_dataset = MyDataset(config.test_data_path, config.test_labels_path)
    test_loader_args = dict(shuffle=False, batch_size=config.atch_size, num_workers=4, collate_fn=val_dataset.collate)
    test_loader = data.DataLoader(test_dataset, **test_loader_args)

    dataloaders_dict = dict(
        train=train_loader,
        val=val_loader,
        test=test_loader,
    )

    return dataloaders_dict

def make_EEG_Image_Map(config):

    dataloaders = make_EEG_Image_data_loaders(config)

    """# **Set up the model**"""
    if config.model == 'mlp':
        model = None
    elif config.model == 'bilstm':
        model = BiLSTM(config.embiddings_num, config.hidden_size, config.num_classes, config.num_layers, config.bidirectional, config.dropout_prob)
    else:
        model = None

    criterion = nn.CTCLoss()    
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=config.wd)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=config.scheduler_factor, patience=config.patience)                

    model.cuda()

    return model, dataloaders, criterion, optimizer, scheduler

def train_and_val_EEG_Image_Map(wandb, config, model, dataloaders, criterion, optimizer, scheduler, num_epochs=50):

    since = time.time()

    val_loss_history = []

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    epoch_loss = None

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch+1, num_epochs))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for inputs, labels, X_length, Y_length in dataloaders[phase]:
                inputs = inputs.cuda()
                labels = labels.cuda()

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    # Run data through the model, Compare output to target
                    outputs = model(inputs)        # (T x B x *)
                    loss = criterion(outputs, labels, X_length, Y_length)

                    _, preds = torch.max(outputs, 1)

                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)

            epoch_loss = running_loss / len(dataloaders[phase].dataset)

            if phase == 'train':
                wandb.log({"epoch": epoch, "train_loss": epoch_loss})
            elif phase == 'val':
                wandb.log({"epoch": epoch, "val_loss": epoch_loss})
            else:
                print('Did not log')
            
            if epoch%(int(num_epochs/10)) == 1:
                print('[{}] Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss))

            # deep copy the model
            if phase == 'val' and epoch_loss < best_loss:
                best_loss = epoch_loss
                best_model_wts = copy.deepcopy(model.state_dict())
            if phase == 'val':
                val_loss_history.append(epoch_loss)

        
        print()

        # Save model every epoch
        filename = 'EEGImageMap' + str(config['model_nr']) + 'epoch' + str(epoch+1) + '.pth'
        torch.save(model.state_dict(), filename)

        scheduler.step(epoch_loss)

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Loss: {:4f}'.format(best_loss))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, val_loss_history

def test_EEG_Image_Map(model, test_loader, criterion):
    model.eval()

    # Run the model on some test examples
    with torch.no_grad():
        predictions = []

        for inputs, labels, X_length, Y_length in test_loader:
            inputs, labels = inputs.cuda(), labels.cuda()
            
            outputs = model(inputs)
            loss = criterion(outputs, labels, X_length, Y_length)

            running_loss += loss.item() * inputs.size(0)

            outputs = outputs.permute(1, 0, 2)              # (B x T x *)
            predictions.append(outputs.cpu().numpy())
            
            del inputs
            del labels
            del X_length
            del Y_length
        
        total_loss = running_loss / len(test_loader.dataset)

        return predictions, total_loss

def get_id_indx(feature, feature_list):
  cos = nn.CosineSimilarity(dim=0)

  # set the first image feature as the best seen so far 
  best_indx = 0
  best_cos = cos(feature, feature_list[0])

  for indx, f in eumerate(feature_list):
    current_cos = cos(feature, f)
    if current_cos > best_cos:
        best_indx = indx
        best_cos = current_cos

  return best_indx

def calc_feature_id_acc(outputs, test_loader):
    """ Calculates image identification accuracy """
    correct = 0.
    all_labels = []

    # make list out of labels in data_loader
    for inputs, labels, X_length, Y_length in test_loader:
        all_labels.append(labels.cpu().numpy())
    
    all_labels_flat = [item for sublist in all_labels for item in sublist]

    # loop through each outputs and 
    for indx, out in enumerate(outputs):
        out_indx = get_id_indx(out, all_labels_flat)
        if indx == out_indx:
            correct += 1

    acc = correct / len(all_labels_flat)
    
    return acc
