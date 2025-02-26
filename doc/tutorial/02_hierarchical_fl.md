# Let FL be Hierarchical
In this section, we are talking about hierarchical node deployment.

Here's the [example code](../../examples/02_hierarchical_pytorch).

Before you dive into the code, let's discuss some information about this section:


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

In this case, we start a master node as a "root". Then, run several zone nodes and declare the master node as their parent. In this point, we have built a flat topology. We can start some client nodes, and declare one of the zone nodes as their parent. Finally, a hierarchical FL topology is built.

For example, the topology can be:
- master
    - zone_1
        - client_1
        - client_2
    - zone_2
        - client_3
        - client_4


### 2. Declare task configurations
Please refer to the task.json from the [example code](../../examples/02_hierarchical_pytorch). It's a little bit different from the [previous tutorilal](./01_quickstart_in_pytorch.md):

1. `NUM_ROUNDS` represents the predefined fit_rounds between the master node and its children. In a hierarchical case, it would be Master `<->` Zones <-> Clients. On the other hand, `ZONE_COMM_FREQUENCY` represents Master <-> Zones `<->` Clients. That is the number of communication rounds between zones and clients within a communication round between master and zones.

2. The master node will wait for `MIN_WAITING_TIME_MASTER` seconds every rounds (between master and zones). Similarly, the zone nodes will wait for `MIN_WAITING_TIME_ZONE` seconds every rounds (between zones and clients).

3. `OPERATORS`, `STRATEGIES`, and `METRICS_HANDLERS` are customized modules, which will be dynamically loaded. We will explain these configurations in the coming tutorials.


### 3. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 4. Shutdown Daisy
We can shutdown each individual node via gRPC.


Now, you can follow the README of the [example code](../../examples/02_hierarchical_pytorch) and start FL training.

Next section: [03_customized_fl_algorithms](./03_customized_fl_algorithms.md)