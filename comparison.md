# Core Difference Analysis: OpenDaisy vs. Daisy (MTLF-daisy)

This document records the core technical differences and architectural comparisons between **OpenDaisy (Open-Source)** and **Daisy (NWDAF-daisy / MTLF-daisy)** before their synchronization.

---

## 1. Overview

*   **OpenDaisy**: Positioned as a general-purpose, lightweight Federated Learning (FL) framework base, focusing on research and basic experimental scenarios.
*   **Daisy (MTLF-daisy)**: An enhanced version deeply customized for 5G NWDAF (Network Data Analytics Function) scenarios, featuring MLOps automation, asynchronous task handling, and deep integration with 5G infrastructure.

---

## 2. Technical Comparison Table

| Dimension | OpenDaisy (Open-Source) | Daisy (MTLF-daisy) |
| :--- | :--- | :--- |
| **Task Execution Mode** | Synchronous Blocking | Asynchronous Background Execution + Webhook Callback |
| **Client Lifecycle** | Manual Management (Manual Boot) | Automated Deployment (Auto-spawning via Subprocess) |
| **Data Access Layer** | No built-in database integration | Integrated MongoDB with `/upload_data` API |
| **Model Initialization** | Static Initialization at startup | Dynamic Construction via `MODEL_META` |
| **Artifact Management** | Local file storage | Automatic packaging (.tar.gz) with HTTP download |
| **Warm-start Support** | Basic weight loading | Supports Seed Model, Fixed Scaler, and TID-based isolation |

---

## 3. Detailed Differences

### A. Asynchronous Task Handling and Webhooks
*   **OpenDaisy**: After a user sends `publish_task`, the Master enters the training loop immediately, keeping the connection open until dozens of training rounds are completed.
*   **Daisy**: Supports `CALLBACK_URL` in the JSON task configuration. The Master returns `202 Accepted` immediately upon receiving the task and executes training in the background. After successful completion, failure, or triggering Early Stopping, it automatically sends a POST request to the callback URL to notify the result.

### B. Automated Client Management (Multi-tenancy Support)
*   **OpenDaisy**: Requires manual startup of client processes on each node.
*   **Daisy**: When the Master receives a task, it automatically queries the `group_id` in MongoDB. For each discovered data group, the Master automatically spawns an independent `client.py` process locally (or on designated nodes). This allows the system to dynamically establish a federated learning topology upon receiving NWDAF requests.

### C. 5G Traffic Data Access and Storage
*   **Daisy Core** implements additional interfaces to interface with 5G Core Network components (e.g., UPF/EES).
    *   **`/upload_data`**: Receives 3GPP-compliant or customized traffic statistics JSON and automatically indexes (`tid`, `group_id`) them into MongoDB.
    *   **Data Isolation**: Achieves data isolation between different training tasks through `TID` (Task ID).

### D. Dynamic Model Construction and Seed Models
*   **Dynamization**: Daisy Core can parse `MODEL_META` in the task configuration. For example:
    *   `input_size`: 10
    *   `num_channels`: [32, 64, 64, 64]
    *   The Master builds the corresponding TCN model directly in memory based on these parameters, eliminating the need to write fixed model class definitions in advance.
*   **Continued Training (Seed Support)**: Supports `SEED_MODEL_PATH` and `SEED_SCALER_PATH`, allowing fine-tuning from existing training artifacts instead of training from scratch.

### E. Automated Artifact Release Pipeline
*   **OpenDaisy**: Training results are scattered in the `model/` folder, requiring manual movement during deployment.
*   **Daisy**: After training, the system automatically packages weight files (`model.npy`), scalers (`scaler.pkl`), model scripts (`model.py`), and metadata into a compressed archive in the `artifacts/` directory and generates a download link.

---

## 4. Summary

The `MTLF-daisy` version evolves Daisy from a simple FL framework into an **ML Microservice Platform** specifically designed for 5G traffic forecasting, realizing full lifecycle management from data access to artifact deployment.
