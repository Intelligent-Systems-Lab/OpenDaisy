# Daisy [MTLF-daisy] - 5G NWDAF MTLF Implementation
This branch (`MTLF-daisy`) is a specialized version of Daisy core designed for **5G NWDAF (Network Data Analytics Function)** and **MTLF (Model Training and Learning Function)** scenarios. It extends the core OpenDaisy framework with professional MLOps automation, asynchronous task handling, and deep integration with 5G infrastructure.

## Key Features (MTLF-daisy)
Compared to the standard OpenDaisy, this branch includes:
- **Asynchronous Task Execution**: Immediate `202 Accepted` response with background training and Webhook callbacks.
- **Automated Client Lifecycle**: Dynamic spawning of client processes based on task configurations and group IDs.
- **5G Data Integration**: Built-in MongoDB support for handling 3GPP-compliant traffic statistics via `/upload_data` API.
- **Dynamic Model Deployment**: On-the-fly model construction using `MODEL_META` without predefined classes.
- **Automated Artifact Management**: Automatic packaging of weights, scalers, and metadata for HTTP download.
- **Warm-start Support**: Native support for Seed Models and Fixed Scalers to enable fine-tuning.

## Who is Daisy [MTLF-daisy] for?
- Researchers implementing 3GPP NWDAF/MTLF specifications.
- Developers needing an automated, production-ready Federated Learning MLOps pipeline for 5G.
- Users requiring asynchronous training workflows and dynamic client management.



## Installation
[For algorithm development (user mode)](doc/installation/user_mode.md): For Daisy users, this document will help you install Daisy in user mode via pip.

[For framework development (dev mode)](doc/installation/dev_mode.md): For Daisy contributors, this document will help you install Daisy in dev mode by building a poetry project.


## Quickstart
Several examples are provided to quickly familiarize Daisy:
- [Quickstart in PyTorch](doc/tutorial/01_quickstart_in_pytorch.md)
- [Let FL be hierarchical](doc/tutorial/02_hierarchical_fl.md)
- [Customize FL algorithms](doc/tutorial/03_customized_fl_algorithms.md)
- [Start FL with asynchronous communication](doc/tutorial/04_asynchronous_fl.md)
- [Upload FL models by proximal transmission](doc/tutorial/05_proximal_transmission.md)
- [Protect FL models using secure aggregation](doc/tutorial/06_secure_aggregation.md)
- [MTLF Training with MongoDB and MLOps](examples/07_MTLF_training/README.md)

