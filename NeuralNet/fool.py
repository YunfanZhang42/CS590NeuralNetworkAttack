import os
import torch
import torchvision
import torchvision.transforms as T
import random
import numpy as np
from scipy.ndimage.filters import gaussian_filter1d
from PIL import Image

SQUEEZENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
SQUEEZENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def make_fooling_image(X, target_y, model):
    """
    Generate a fooling image that is close to X, but that the model classifies
    as target_y.

    Inputs:
    - X: Input image; Tensor of shape (1, 3, 224, 224)
    - target_y: An integer in the range [0, 1000)
    - model: A pretrained CNN

    Returns:
    - X_fooling: An image that is close to X, but that is classifed as target_y
    by the model.
    """
    X_fooling = X.clone()
    X_fooling = X_fooling.requires_grad_()

    learning_rate = 1
    y = torch.tensor([target_y])
    fooled_count = 0
    for i in range(100):
        out = model(X_fooling)
        if out.data.max(1)[1][0].item() == target_y:
            fooled_count += 1
            if fooled_count == 5:
                return X_fooling
        else:
            fooled_count = 0
        out[0, target_y].backward()
        g = X_fooling.grad

        # normalize
        dX = learning_rate * g / torch.norm(g)
        X_fooling = X_fooling.detach() + dX
        X_fooling.requires_grad_()
    return X_fooling

def load_imagenet_val(num=None):
    imagenet_fn = 'imagenet_val_25.npz'
    f = np.load(imagenet_fn)
    X = f['X']
    y = f['y']
    class_names = f['label_map'].item()
    if num is not None:
        X = X[:num]
        y = y[:num]
    return X, y, class_names

def preprocess(img, size=224):
    transform = T.Compose([
        T.Resize(size),
        T.ToTensor(),
        T.Normalize(mean=SQUEEZENET_MEAN.tolist(),
                    std=SQUEEZENET_STD.tolist()),
        T.Lambda(lambda x: x[None]),
    ])
    return transform(img)

def deprocess(img, should_rescale=True):
    transform = T.Compose([
        T.Lambda(lambda x: x[0]),
        T.Normalize(mean=[0, 0, 0], std=(1.0 / SQUEEZENET_STD).tolist()),
        T.Normalize(mean=(-SQUEEZENET_MEAN).tolist(), std=[1, 1, 1]),
        T.Lambda(rescale) if should_rescale else T.Lambda(lambda x: x),
        T.ToPILImage(),
    ])
    return transform(img)

X, y, class_names = load_imagenet_val(num=100)

def fool(img, target):
    model = torchvision.models.squeezenet1_1(pretrained=True)
    for param in model.parameters():
        param.requires_grad = False

    X_tensor = torch.cat([preprocess(img)], dim=0)
    X_fooling = make_fooling_image(X_tensor, target, model)
    scores = model(X_fooling)
    assert target == scores.data.max(1)[1][0].item(), 'The model is not fooled!'

def load_image():
    img = Image.open('images/dog.png')
    return img

def save_Image():
    img = Image.fromarray(X[3], 'RGB')
    img.save("3.png")

# save_Image()
fool(load_image(), 100)