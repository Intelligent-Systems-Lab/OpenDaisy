# Daisy - A Novel Federated Learning Framework for Edge-Driven AIoT Model Development
Daisy is a federated learning (FL) framework designed to provide hierarchical, distributed node deployment, integrating technologies such as 5G and multi-access edge computing (MEC). It addresses issues like mobility, unstable networks, and inconsistent data availability for mobile smart agents such as vehicles and robots. Daisy offers the following advantages:

- Flexibility: Daisy supports both star topology and hierarchical topology.
- Reliability: Daisy accounts for unstable network environments and offers a connection recovery mechanism.
- Mobility-aware: Daisy allows mobile clients to upload their local models to nearby edge servers, significantly reducing communication costs, minimizing latency, and improving upload success rates.


## Who is Daisy for?
Daisy is highly extensible, enabling users and developers to port most existing FL algorithms. We particularly recommend Daisy for researchers and developers working in the following scenarios:

- Traditional FL
- Hierarchical FL
- FL with unstable networks
- FL with mobile clients
- Asynchronous FL


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

