# -*- coding: utf-8 -*-
"""Image-Net.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1EWipdCiT5DnR_6Rp46yOaQFmpFnE_ker

# Image-Net

Reference: https://pytorch.org/tutorials/beginner/finetuning_torchvision_models_tutorial.html
"""

"""# Imports"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils import data
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
import time
import os
import copy


"""Set Model Parameters’ .requires_grad attribute"""

def set_parameter_requires_grad(model, feature_extracting):
    if feature_extracting:
        for param in model.parameters():
            param.requires_grad = False

"""Initialize and Reshape the Networks"""

def initialize_model(model_name, num_classes, feature_extract, use_pretrained=True):
    # Initialize these variables which will be set in this if statement. Each of these
    #   variables is model specific.
    model_ft = None
    input_size = 0

    if model_name == "resnet":
        """ Resnet18
        """
        model_ft = models.resnet18(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        num_ftrs = model_ft.fc.in_features
        model_ft.fc = nn.Linear(num_ftrs, num_classes)
        input_size = 224

    elif model_name == "alexnet":
        """ Alexnet
        """
        model_ft = models.alexnet(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        num_ftrs = model_ft.classifier[6].in_features
        model_ft.classifier[6] = nn.Linear(num_ftrs,num_classes)
        input_size = 224

    elif model_name == "vgg":
        """ VGG11_bn
        """
        model_ft = models.vgg11_bn(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        num_ftrs = model_ft.classifier[6].in_features
        model_ft.classifier[6] = nn.Linear(num_ftrs,num_classes)
        input_size = 224

    elif model_name == "squeezenet":
        """ Squeezenet
        """
        model_ft = models.squeezenet1_0(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        model_ft.classifier[1] = nn.Conv2d(512, num_classes, kernel_size=(1,1), stride=(1,1))
        model_ft.num_classes = num_classes
        input_size = 224

    elif model_name == "densenet":
        """ Densenet
        """
        model_ft = models.densenet121(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        num_ftrs = model_ft.classifier.in_features
        model_ft.classifier = nn.Linear(num_ftrs, num_classes)
        input_size = 224

    elif model_name == "inception":
        """ Inception v3
        Be careful, expects (299,299) sized images and has auxiliary output
        """
        model_ft = models.inception_v3(pretrained=use_pretrained)
        set_parameter_requires_grad(model_ft, feature_extract)
        # Handle the auxilary net
        num_ftrs = model_ft.AuxLogits.fc.in_features
        model_ft.AuxLogits.fc = nn.Linear(num_ftrs, num_classes)
        # Handle the primary net
        num_ftrs = model_ft.fc.in_features
        model_ft.fc = nn.Linear(num_ftrs,num_classes)
        input_size = 299

    else:
        print("Invalid model name, exiting...")
        exit()

    return model_ft, input_size


"""# Data Loading"""
# Create dataset for Images using EEG data
class ImageDataset(data.Dataset):
    def __init__(self, image_data, EEG_data, transform):
        self.image_data = image_data
        self.EEG_data = EEG_data
        self.image_ids = list(EEG_data.keys())
        self.transform = transform
        self.length = len(self.image_ids)

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        image_id = self.image_ids[index]
        image = self.transform(self.image_data[image_id])
        label = self.EEG_data[image_id][0]['label']
        return image, label

class EEG_to_ImageDataset(data.Dataset):
    def __init__(self, image_data, EEG_dataset, transform):
        self.image_data = image_data
        self.EEG_dataset = EEG_dataset
        self.transform = transform
        self.length = len(self.EEG_dataset)

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        data_entry = self.EEG_dataset.data_list[index]
        image_id = data_entry['image']
        image = self.transform(self.image_data[image_id])
        label = data_entry['label']
        return image, label


"""# Module functions """
def make_Image_data_loaders(config, eeg_path, image_path, input_size):
    # Load image data
    data_by_image = torch.load(image_path)
    # Convert images back to PIL to be able to transform (crop)
    data_by_image = {i: transforms.ToPILImage()(data_by_image[i]).convert("RGB") for i in data_by_image}

    # Load EEG datasets
    eeg_datasets = torch.load(eeg_path)

    # Data augmentation and normalization for training
    # Just normalization for validation
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(input_size),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    train_image_dataset = ImageDataset(data_by_image, eeg_datasets['train'], data_transforms['train'])
    train_image_loader_args = dict(shuffle=True, batch_size=config['batch_size'], num_workers=2) 
    train_image_loader = data.DataLoader(train_image_dataset, **train_image_loader_args)

    val_image_dataset = ImageDataset(data_by_image, eeg_datasets['val'], data_transforms['val'])
    val_image_loader_args = dict(shuffle=False, batch_size=config['batch_size'], num_workers=2)
    val_image_loader = data.DataLoader(val_image_dataset, **val_image_loader_args)

    test_image_dataset = ImageDataset(data_by_image, eeg_datasets['test'], data_transforms['val'])
    test_image_loader_args = dict(shuffle=False, batch_size=config['batch_size'], num_workers=2)
    test_image_loader = data.DataLoader(test_image_dataset, **test_image_loader_args)

    dataloaders_dict = dict(
        train=train_image_loader,
        val=val_image_loader,
        test= test_image_loader,
    )

    del eeg_datasets
    del data_by_image

    return dataloaders_dict

def make_EEG_to_Image_data_loaders(eeg_loaders, image_path, input_size):
    # Load image data
    data_by_image = torch.load(image_path)
    # Convert images back to PIL to be able to transform (crop)
    data_by_image = {i: transforms.ToPILImage()(data_by_image[i]).convert("RGB") for i in data_by_image}

    # Data augmentation and normalization for training
    # Just normalization for validation
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(input_size),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    train_image_dataset = EEG_to_ImageDataset(data_by_image, eeg_loaders['train'].dataset, data_transforms['val'])
    train_image_loader_args = dict(shuffle=False, batch_size=128, num_workers=2) 
    train_image_loader = data.DataLoader(train_image_dataset, **train_image_loader_args)

    val_image_dataset = EEG_to_ImageDataset(data_by_image, eeg_loaders['val'].dataset, data_transforms['val'])
    val_image_loader_args = dict(shuffle=False, batch_size=128, num_workers=2)
    val_image_loader = data.DataLoader(val_image_dataset, **val_image_loader_args)

    test_image_dataset = EEG_to_ImageDataset(data_by_image, eeg_loaders['test'].dataset, data_transforms['val'])
    test_image_loader_args = dict(shuffle=False, batch_size=128, num_workers=2)
    test_image_loader = data.DataLoader(test_image_dataset, **test_image_loader_args)

    dataloaders_dict = dict(
        train_unshuffle=train_image_loader,
        val=val_image_loader,
        test= test_image_loader,
    )

    del data_by_image

    return dataloaders_dict

def make_Image_Net(config, eeg_path, image_path):
    model, input_size = initialize_model(config['model_name'], config['num_classes'], config['feature_extract'], use_pretrained=True)
    
    dataloaders = make_Image_data_loaders(config, eeg_path, image_path, input_size)

    # Send the model to GPU
    model = model.cuda()

    # Gather the parameters to be optimized/updated in this run. If we are
    #  finetuning we will be updating all parameters. However, if we are
    #  doing feature extract method, we will only update the parameters
    #  that we have just initialized, i.e. the parameters with requires_grad
    #  is True.
    params_to_update = model.parameters()
    print("Params to learn:")
    if config['feature_extract']:
        params_to_update = []
        for name,param in model.named_parameters():
            if param.requires_grad == True:
                params_to_update.append(param)
                print("\t",name)
    else:
        for name,param in model.named_parameters():
            if param.requires_grad == True:
                print("\t",name)

    # Observe that all parameters are being optimized
    optimizer = optim.SGD(params_to_update, lr=config['lr'], momentum=0.9)

    # Setup the loss fxn
    criterion = nn.CrossEntropyLoss()

    return model, dataloaders, criterion, optimizer

def train_and_val_Image_Net(wandb, config, model, dataloaders, criterion, optimizer, is_inception=False):
    since = time.time()

    val_acc_history = []

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    for epoch in range(config['num_epochs']):
        print('Epoch {}/{}'.format(epoch+1, config['num_epochs']))
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
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.cuda()
                labels = labels.cuda()

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    # Get model outputs and calculate loss
                    # Special case for inception because in training it has an auxiliary output. In train
                    #   mode we calculate the loss by summing the final output and the auxiliary output
                    #   but in testing we only consider the final output.
                    if is_inception and phase == 'train':
                        # From https://discuss.pytorch.org/t/how-to-optimize-inception-model-with-auxiliary-classifiers/7958
                        outputs, aux_outputs = model(inputs)
                        loss1 = criterion(outputs, labels)
                        loss2 = criterion(aux_outputs, labels)
                        loss = loss1 + 0.4*loss2
                    else:
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)

                    _, preds = torch.max(outputs, 1)

                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.double() / len(dataloaders[phase].dataset)

            if phase == 'train':
                wandb.log({"epoch": epoch, "train_loss": epoch_loss, "train_acc": epoch_acc})
            elif phase == 'val':
                wandb.log({"epoch": epoch, "val_loss": epoch_loss, "val_acc": epoch_acc})
            else:
                print('Did not log')
            print('[{}] Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
            if phase == 'val':
                val_acc_history.append(epoch_acc)

        
        print()

        # Save model every epoch
        filename = 'ImageNet' + str(config['model_nr']) + 'epoch' + str(epoch+1) + '.pth'
        torch.save(model.state_dict(), filename)

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, val_acc_history

def test_Image_Net(model, test_loader):
    model.eval()

    # Run the model on some test examples
    with torch.no_grad():
        correct, total = 0., 0
        predictions = []
        all_features = []

        for inputs, labels in test_loader:
            inputs, labels = inputs.cuda(), labels.cuda()
            
            outputs = model(inputs)

            _, predicted = torch.max(outputs.data, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            predictions.append(predicted.cpu().numpy())
            all_features.append(outputs.cpu().numpy())
            
            del inputs
            del labels

        acc = correct / total
        return predictions, all_features, acc


