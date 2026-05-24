# 07_MTLF_training: UPF UE Volume Forecasting with TCN

A unified DaisyFL framework for **Temporal Convolutional Network (TCN)** based **UE Uplink/Downlink Volume Forecasting**, using UPF Event Exposure Service (EES) notifications.

## Installation

Ensure Daisy is installed in [user mode](../../doc/installation/user_mode.md) or [dev mode](../../doc/installation/dev_mode.md).

```bash
pip install -r requirements.txt
```

## Quick Start

The framework supports both baseline (single-domain) and universal (multi-domain) training via the `--data_dirs` argument.

### 1. Start the Training Server (Deploy)

Modify `nodes.yaml` for your topology, then initialize the model and start the master/clients:

**Baseline (Single-Domain, Default):**
```bash
python deploy.py --init_model
```

**Universal (Multi-Domain):**
```bash
python deploy.py --init_model --data_dirs ees_training_data cat123_training_data
```

### 2. Submit the FL Task

```bash
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task
```

### 3. Shutdown

Graceful shutdown of all nodes (happens automatically on early stopping):
```bash
python shutdown.py
```

### Isolated Model Saving & Async Callbacks
By supplying the `--training_name` argument, aour asynchronous requests fetch the precisely partitioned `.tar.gz` payloll trained artifacts are isolated within a dedicated `model/<training_name>/` sub-directory. This seamlessly integrates with DaisyFL's Async Callback packaging, ensuring that yad.
```bash
# Example: Training a combined cat1+cat2 model into an isolated directory
python deploy.py --init_model --data_dirs cat1 cat2 --training_name cat1_cat2_run
python request.py --json=task.json --api=http://0.0.0.0:9887/publish_task --training_name cat1_cat2_run
```


## Architecture Overview

- **Pipeline**: Extracts 10 features, applies `log1p()` & `StandardScaler` (saved to `model/scaler.pkl`), and uses isolated `ue_ip` sliding windows (seq=30). Universal mode fits a single global scaler across all domains.
- **Model**: TCN with 4 `TemporalBlock` layers (dilations: 1, 2, 4, 8) and a linear head.
- **Config**: Defined in `task.json`. Uses `EarlyStoppingFedAvg` (Huber Loss for training, MSE/MAE for eval) with early-stopping patience and `ReduceLR`.

## Key Files

- `nodes.yaml` & `task.json`: Topology and FL task configurations.
- `model.py` & `dataset.py`: TCN architecture and data processing logic.
- `master.py` & `client.py`: DaisyFL Server and Client implementations.
- `deploy.py` / `request.py` / `shutdown.py`: Execution workflow scripts.
- `run_all.py`: Orchestrates multi-GPU sequential training workflows.
- `evaluate_single.py` / `cross_evaluate.py`: Evaluation scripts determining literal volume MAE/MSE and generating prediction plots.
- `model/`: Output directory supporting isolated `model/<training_name>/` structure for `.npy` (weights) and `scaler.pkl`.
