# Let FL be hierarchical
Please ensure Daisy is installed in either [user mode](../../doc/installation/user_mode.md) or [dev mode](../../doc/installation/dev_mode.md).

## Installation
```commandline
pip install -r requirements.txt
```

## Deployment
Modify "**nodes.yaml**" and run the following command:
```commandline
python deploy.py --init_model
```

## Take a FL task
```commandline
python request.py --json=task.json --api=<master_node_api>/publish_task
```
"master_node_api" has a default value of http://0.0.0.0:9887.

## Gracefully Shutdown
Gracefully shutdown Daisy after the task would have been done.
```commandline
python shutdown.py
```

