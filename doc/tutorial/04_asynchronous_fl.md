# Asynchronous FL
If the response times from FL clients vary a lot, asynchronous FL will be an option for task owner. Using this approach, FL task continuously works without waiting for stragglers, leading to shorter training time.

Daisy supports AsyncFL algorithms. Let's review the differences between AsyncFL and FedAvg.

Firstly, we define how many times zone or master node will wait for its children at `strategy.wait_fit`. When using FedAvg, we will check how many clients upload their results to decide the waiting time. On the other hand, we can wait for a static time interval to periodically dispatch FL models.

Secondly, we can pass the arguments to `strategy.aggregate_fit` and compute the staleness and weights to update global model.

Now, let's have our [AsyncFL](../../examples/04_fedasync_pytorch) task.


### 1. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 2. Shutdown Daisy
We can shutdown each individual node via gRPC.


Next section: [05_proximal_transmission](./05_proximal_transmission.md)