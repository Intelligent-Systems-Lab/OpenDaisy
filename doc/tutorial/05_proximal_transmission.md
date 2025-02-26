# Proximal Transmission
Consider a scenario that clients upload their local models to the zone node, from where they downloaded the global model, while they get to a remote site. That sounds inefficient because of the long path while model uploading.

Daisy allows clients to upload their model by `proximal transmission`. Let the zone node, from where clients downloaded global model, be the `anchor`. When clients move to where another proximal zone is located at, clients can associate with the proximal zone and try to upload thier local models to it. The proximal zone will synchronize some management information with the anchor zone to ensure the effectiveness. By `proximal transmission`, we achieve a more efficient FL workflow.


### 1. Roaming
Please refer to the [example code](../../examples/05_proximal_transmission_pytorch). In this example, we decide which clients will roam across zones from `strategy.configure_fit`. In the real world, it can be decided by the location of clients. If a client_instruction contains `TRANSITION`, the corresponding client will try to associate with the other zone and upload its local model by calling `self.handover_fn(<zone_server_address>)` at client_logics operator.


### 2. Run your FL task
We can send a HTTP request to the master node's API gateway to start FL tasks. This API gateway has a default value of http://0.0.0.0:9887.
```
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```


### 3. Shutdown Daisy
We can shutdown each individual node via gRPC.


Next section: [06_secure_aggregation](./06_secure_aggregation.md)