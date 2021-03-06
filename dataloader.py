import os
import numpy as np
import pandas as pd
import tensorflow as tf

from augment import SimAugment
from augment import RandAugment

AUTO = tf.data.experimental.AUTOTUNE


def set_dataset(args):
    trainset = pd.read_csv(
        os.path.join(
            args.data_path, '{}_trainset.csv'.format(args.dataset)
        )).values.tolist()
    valset = pd.read_csv(
        os.path.join(
            args.data_path, '{}_valset.csv'.format(args.dataset)
        )).values.tolist()
    return np.array(trainset, dtype='object'), np.array(valset, dtype='object')

#############################################################################
def fetch_dataset(path, y):
    x = tf.io.read_file(path)
    return tf.data.Dataset.from_tensors((x, y))

def dataloader(args, datalist, mode, batch_size, shuffle=True):
    '''dataloader for cross-entropy loss
    '''    
    def augmentation(img, label, shape):
        if args.augment == 'sim':
            augment = SimAugment(args, mode)
        elif args.augment == 'rand':
            augment = RandAugment(args, mode)

        img = augment(img, shape)
        
        # one-hot encodding
        label = tf.one_hot(label, args.classes)
        return img, label

    def preprocess_image(img, label):
        shape = tf.image.extract_jpeg_shape(img)
        img = tf.io.decode_jpeg(img, channels=3)
        img, label = augmentation(img, label, shape)
        return (img, label)

    imglist, labellist = datalist[:,0].tolist(), datalist[:,1].tolist()
    imglist = [os.path.join(args.data_path, i) for i in imglist]

    dataset = tf.data.Dataset.from_tensor_slices((imglist, labellist))
    dataset = dataset.repeat()
    if shuffle:
        dataset = dataset.shuffle(len(datalist))

    dataset = dataset.interleave(fetch_dataset, num_parallel_calls=AUTO)
    dataset = dataset.map(preprocess_image, num_parallel_calls=AUTO)
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(AUTO)
    return dataset


def dataloader_supcon(args, datalist, mode, batch_size, shuffle=True):
    '''dataloader for supervised contrastive loss
    '''
    def augmentation(img, shape):
        if args.augment == 'sim':
            augment = SimAugment(args, mode)
        elif args.augment == 'rand':
            augment = RandAugment(args, mode)
        
        result = []
        for _ in range(2):
            aug_img = tf.identity(img)
            aug_img = augment(aug_img, shape)
            result.append(aug_img)
        return result

    def preprocess_image(img, label):
        shape = tf.image.extract_jpeg_shape(img)
        img = tf.io.decode_jpeg(img, channels=3)
        anchor, aug_img = augmentation(img, shape)
        return (anchor, aug_img), [label]

    imglist, labellist = datalist[:,0].tolist(), datalist[:,1].tolist()
    imglist = [os.path.join(args.data_path, i) for i in imglist]

    dataset = tf.data.Dataset.from_tensor_slices((imglist, labellist))
    dataset = dataset.repeat()
    if shuffle:
        dataset = dataset.shuffle(len(datalist))

    dataset = dataset.interleave(fetch_dataset, num_parallel_calls=AUTO)
    dataset = dataset.map(preprocess_image, num_parallel_calls=AUTO)
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(AUTO)
    return dataset