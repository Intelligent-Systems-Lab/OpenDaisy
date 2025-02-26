# Customized FL Algorithms
You can run the example codes now, but it's not enough to develop your FL algorithm.

In this section, we will introduce the customized modules, which will be dynamically loaded, to you.

Here's the [example code](../../examples/03_customized_algorithms_pytorch).

Before you dive into the code, let's find the difference between this example and the previous one:


### 1. Declare task configurations
Please refer to the task.json from the [example code](../../examples/03_customized_algorithms_pytorch). It's a little bit different from the [previous tutorilal](./02_hierarchical_fl.md):

The sections of `OPERATORS`, `STRATEGIES`, and `METRICS_HANDLERS` in the task.config were described as some daisyfl module paths. However, we use our own paths here in this time.

The declared modules will be dynamically loaded in the runtime. One of the benefits of this design is that multi-task FL will be allowed using Daisy.

If our own modules are loaded, we will see some differences in the log.

### 2. Customized modules overview
We are introducing the functionalities of these customized modules so that we can take advantages of their interfaces to develop our FL algorithms.

`Operators` is a core module of Daisy. It defines the operation logics of each Daisy node. While start a task, we need to tell the master node the paths of operators for each node type.

`Strategy` contains the interfaces that defines
1. how we find the children to participate FL,
2. we are waiting for how many times and how many results, and
3. how we aggregate the results.

`MetricsHandler` records the FL metrics so that we can export them via HTTP gateway.


### 3. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 4. Shutdown Daisy
We can shutdown each individual node via gRPC.


Now, you can follow the README of the [example code](../../examples/03_customized_algorithms_pytorch) and start FL training.

Next section: [04_interactive_fl_nodes](./04_asynchronous_fl.md)