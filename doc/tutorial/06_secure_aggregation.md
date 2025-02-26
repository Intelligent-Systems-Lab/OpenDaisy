# Secure Aggregation
Daisy allows us to encrypt our local models by secure aggregation. There are many stages in secure aggregation:

0. Setup SecAgg parameters.
1. Zone asks for clients' public keys.
2. Zone distributes t-out-of-n KeyShares.
3. Zone asks for masked local models.
4. Unmask the local models according to the state of each client.

Zone nodes declare the stage index in the client_instructions so that clients can execute the corresponding algorithm by stage index.

Now, let's have our [SecAgg](../../examples/06_secure_aggregation_pytorch) task.


### 1. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 2. Shutdown Daisy
We can shutdown each individual node via gRPC.
