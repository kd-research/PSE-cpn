import json
import pickle
import numpy as np
import tensorflow as tf
from pathlib import Path


def custom_dataset(nframe=18, nagent=30, nhead=8):
    class PickledLatent:
        def __init__(self, arr, nframe=nframe, nagent_max=nagent):
            self.name = arr[0]
            self.param = arr[1]
            raw_latent = arr[2]
            raw_nagent = raw_latent.shape[0] // nframe
            raw_latent = raw_latent.reshape(nframe, raw_nagent, nhead)
            latent = np.pad(raw_latent, ((0, 0), (0, nagent_max - raw_nagent), (0, 0)))
            self.latent = latent.reshape(-1, nhead)

        def __str__(self):
            return f"name: {self.name}, latent shape: {self.latent.shape}"

    class JsonLatent:
        def __init__(self, arr, nframe=nframe, nagent_max=nagent):
            self.name = arr['seq_name']
            self.param = np.asarray(arr['env_param'])
            raw_latent = np.asarray(arr['context_v'])
            raw_nagent = raw_latent.shape[0] // nframe
            raw_latent = raw_latent.reshape(nframe, raw_nagent, nhead)
            latent = np.pad(raw_latent, ((0, 0), (0, nagent_max - raw_nagent), (0, 0)))
            self.latent = latent.reshape(-1, nhead)
            self.zlatent = np.asarray(arr['z']).T.reshape((-1, 1))

        def __str__(self):
            return f"name: {self.name}, latent shape: {self.latent.shape}"


    class TrainDataset:
        def __init__(self, pickled_objects, batch_size=256):
            parameters = [x.param for x in pickled_objects]
            latents = [x.latent for x in pickled_objects]
            self.dataset = tf.data.Dataset.from_tensor_slices((latents, parameters))
            self.batch_size = batch_size

        def prepare(self, shuffle=False, batch_size=None):
            AUTOTUNE = tf.data.AUTOTUNE
            ds = self.dataset

            if shuffle:
                ds = ds.shuffle(1000)

            target_batch_size = batch_size if batch_size is not None else self.batch_size
            target_batch_size = min(target_batch_size, 1)
            # Batch all datasets.
            ds = ds.batch(target_batch_size)

            # Use buffered prefetching on all datasets.
            return ds.prefetch(buffer_size=AUTOTUNE)

    return [PickledLatent, JsonLatent], TrainDataset


def load_dataset(filename, nframe, nagent, nhead, batch_size=128, len_out={}):
    (PickledLatent, JsonLatent), TrainDataset = custom_dataset(nframe=nframe, nagent=nagent, nhead=nhead)
    if Path(filename).suffix == '.pkl':
        with open(filename, "rb") as f:
            obj = pickle.load(f)
        pobj = list(map(PickledLatent, obj))
    elif Path(filename).suffix == '.json':
        with open(filename, "rb") as f:
            obj = [json.loads(line) for line in f.readlines()]
        pobj = list(map(JsonLatent, obj))

    len_out['len_out'] = len(pobj)

    return TrainDataset(pobj, batch_size=batch_size)
