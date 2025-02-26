# Quickstart in PyTorch
Welcome to using Daisy for your Federated Learning (FL) tasks. In this guide, we'll discuss how to build a simple hub-and-spoke FL topology and walk you through setting up a basic configuration to run your task.

Here's the [example code](../../examples/01_quickstart_pytorch).

Before you dive into the code, here are a few things you should know:


### 1. Build up your FL topology
We can call the following APIs to start a Daisy node:
```
# master node
daisyfl.master.start_master(
    server_address,
    api_ip,
    api_port,
)
```
```
daisyfl.zone.start_zone(
    parent_address,
    server_address,
)
```
```
daisyfl.client.start_client_numpy(
    server_address,
    parent_address,
    numpy_trainer,
    metadata,
)
```

When you start a master node, it will be a "root". On the other hand, when you initiate a zone node or a client node, it will try connecting to the "parrent" to build up a FL topology. For example, we make two client nodes connect to a master node in this case.

However, building up FL topology and running a FL task are different things in Daisy. Thus, we are proceeding with declarative task configurations.


### 2. Declare task configurations
Please refer to the task.json from the [example code](../../examples/01_quickstart_pytorch). It's an example of task configurations.
1. `TID` is a unique ID of your task.

2. `NUM_ROUNDS` represents the predefined fit_rounds between the master node and its children. In a hierarchical case, it would be Master `<->` Zones <-> Clients. However, in this hub-and-spoke case, it would be Master `<->` Clients.

3. `EVALUATE_INTERVAL` is the interval of the master node's fit_rounds, at which we will evaluate the global model once.

4. If `EVALUATE_INIT_MODEL_MASTER` is set to "true", the initial global model will be evaluated.

5. The master node will wait for `MIN_WAITING_TIME_MASTER` seconds every fit_rounds and evaluate_rounds. Thus, be patient and wait for the proceeded task please.

6. We need to tell the master node where the initial global model is. It's required to be a .npy file, and to be put on `MODEL_PATH`. In this case, we can pass a flag when we run `python deploy.py --init_model` to prepare this file.

7. `OPERATORS`, `STRATEGIES`, and `METRICS_HANDLERS` are customized modules, which will be dynamically loaded. We will explain these configurations in the coming tutorials.

8. The master node will overwrite the `MODEL_PATH` using the up-to-date global model if `SAVE_MODEL` is set to "true".


### 3. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 4. Shutdown Daisy
We can shutdown each individual node via gRPC.


Now, you can follow the README of the [example code](../../examples/01_quickstart_pytorch) and start FL training.

Next section: [02_hierarchical_fl](./02_hierarchical_fl.md)