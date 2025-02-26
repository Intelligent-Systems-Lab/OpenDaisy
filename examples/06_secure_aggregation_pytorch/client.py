import warnings
from collections import OrderedDict

import daisyfl as fl
from model import Net
import torch
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor
from tqdm import tqdm
from daisyfl.common import (
    METRICS,
    LOSS,
    CID,
    ACCURACY,
    DATA_SAMPLES,
)
import argparse
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--server_address", type=str, help="my grpc server port")
parser.add_argument("--parent_address", type=str, help="for grpc connection")
args = parser.parse_args()

# #############################################################################
# 1. Regular PyTorch pipeline: nn.Module, train, test, and DataLoader
# #############################################################################

warnings.filterwarnings("ignore", category=UserWarning)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def train(net, trainloader, epochs):
    """Train the model on the training set."""
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
    for _ in range(epochs):
        for images, labels in tqdm(trainloader):
            optimizer.zero_grad()
            criterion(net(images.to(device)), labels.to(device)).backward()
            optimizer.step()


def test(net, testloader):
    """Validate the model on the test set."""
    criterion = torch.nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0
    with torch.no_grad():
        for images, labels in tqdm(testloader):
            outputs = net(images.to(device))
            labels = labels.to(device)
            loss += criterion(outputs, labels).item()
            total += labels.size(0)
            correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()
    return loss / len(testloader.dataset), correct / total


def load_data():
    """Load CIFAR-10 (training and test set)."""
    trf = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    trainset = CIFAR10("./data", train=True, download=True, transform=trf)
    testset = CIFAR10("./data", train=False, download=True, transform=trf)
    return DataLoader(trainset, batch_size=32, shuffle=True), DataLoader(testset)


# #############################################################################
# 2. Federation of the pipeline with Daisy
# #############################################################################

# Load model and data (simple CNN, CIFAR-10)
net = Net().to(device)
trainloader, testloader = load_data()

class DaisyTrainer(fl.client.NumPyTrainer):
    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        net.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        train(net, trainloader, epochs=1)
        config[METRICS] = { DATA_SAMPLES: len(trainloader.dataset) }
        return self.get_parameters(config={}), config

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        loss, accuracy = test(net, testloader)
        config[METRICS] = {
            ACCURACY: accuracy,
            LOSS: loss,
            DATA_SAMPLES: len(testloader.dataset)
        }
        return config

metadata = (
    (CID, str(uuid.uuid4())),
)

if __name__=='__main__':
    # Start Daisy client
    fl.client.start_client_numpy(
        server_address=args.server_address,
        parent_address=args.parent_address,
        numpy_trainer=DaisyTrainer(),
        metadata=metadata,
    )
