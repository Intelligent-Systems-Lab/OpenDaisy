## FL Topologies in Daisy
We can declare a traditional (hub-and-spoke) FL topology like

![](../img/flat.png)

that we directly connect Client nodes to the Master node. Moreover, Daisy supports for hierarchical FL like

![](../img/hier.png)

For the details, the operational flows in these nodes are like

### Master
```mermaid
sequenceDiagram
    participant ServerApiHandler
    participant TaskManager
    participant ServerOperator
    participant Strategy
    participant MetricsHandler
    participant Communicator
    participant gRPCClientProxy
    actor Children
    ServerApiHandler->>TaskManager: 1. assign a task
    TaskManager->>TaskManager: 2. divide the task to subtasks
    loop 
        TaskManager->>ServerOperator: 3. assign a subTask
        ServerOperator->>Strategy: 4. request for a set of client_proxies
        Strategy->>ServerOperator: 5. return a set of client_proxies
        ServerOperator->>Communicator: 6. request for sending messages
        par
            Communicator->>gRPCClientProxy: 7. pass the instruction
            gRPCClientProxy->>+Children: 8. send the instruction
            Children->>-gRPCClientProxy: 9. return the result
            gRPCClientProxy->>Communicator: 10. pass the result
        end
        Communicator->>ServerOperator: 11. return all results
        ServerOperator->>Strategy: 12. request for aggregating the results
        Strategy->>ServerOperator: 13. return the aggregated model
        ServerOperator->>MetricsHandler: 14. Record metrics
        ServerOperator->>TaskManager: 15. return the aggregated model 
        TaskManager->>TaskManager: 16. update the global model
    end
```
### Zone
```mermaid
sequenceDiagram
    actor Parent
    participant gRPCClient
    participant TaskManager
    participant ServerOperator
    participant Strategy
    participant MetricsHandler
    participant Communicator
    participant gRPCClientProxy
    actor Children
    Parent->>gRPCClient: 1. send the instruction
    gRPCClient->>TaskManager: 2. assign a subtask
    loop 
        TaskManager->>ServerOperator: 3. assign a subtask
        ServerOperator->>Strategy: 4. request for a set of client_proxies
        Strategy->>ServerOperator: 5. return a set of client_proxies
        ServerOperator->>Communicator: 6. request for sending messages
        par
            Communicator->>gRPCClientProxy: 7. pass the instruction
            gRPCClientProxy->>+Children: 8. send the instruction
            Children->>-gRPCClientProxy: 9. return the result
            gRPCClientProxy->>Communicator: 10. pass the result
        end
        Communicator->>ServerOperator: 11. return all results
        ServerOperator->>Strategy: 12. request for aggregating the results
        Strategy->>ServerOperator: 13. return the aggregated model
        ServerOperator->>MetricsHandler: 14. Record metrics
        ServerOperator->>TaskManager: 15. return the aggregated model
        TaskManager->>TaskManager: 16. update the zone model
    end
    TaskManager->>gRPCClient: 17. return the result
    gRPCClient->>Parent: 18. return the result
```
### Client
```mermaid
sequenceDiagram
    actor Parent
    Parent->>ClientOperator: 1. send an instruction
    ClientOperator->>Trainer: 2. pass the instruction
    Trainer->>ClientOperator: 3. return the result
    ClientOperator->>Parent: 4. return the result
```

