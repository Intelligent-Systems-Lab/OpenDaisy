# OpenDaisy vs. Daisy (MTLF-daisy) 核心差異分析報告

本文件記錄了 **OpenDaisy (Open-Source)** 與 **Daisy (NWDAF-daisy / MTLF-daisy)** 在同步合併前的核心技術差異與架構設計對比。

---

## 1. 概觀 (Overview)

*   **OpenDaisy**: 定位為通用的、輕量級聯邦學習 (FL) 框架基礎，專注於研究與基礎實驗場景。
*   **Daisy (MTLF-daisy)**: 針對 5G NWDAF (Network Data Analytics Function) 場景深度客製化的增強版本，具備 MLOPs 自動化、非同步任務處理以及與 5G 基礎設施深度整合的能力。

---

## 2. 核心技術差異比較表

| 維度 | OpenDaisy (Open-Source) | Daisy (MTLF-daisy) |
| :--- | :--- | :--- |
| **任務執行模式** | 同步阻塞 (Synchronous Blocking) | 非同步背景執行 (Async) + Webhook 回呼 |
| **Client 生命週期** | 手動管理 (Manual Boot) | 自動化部署 (Auto-spawning via Subprocess) |
| **資料接入層** | 無內建資料庫整合 | 整合 MongoDB，具備 `/upload_data` API |
| **模型初始化** | 啟動時預載 (Static Init) | 動態建構 (Dynamic via `MODEL_META`) |
| **Artifact 管理** | 本地檔案存儲 | 自動打包 (.tar.gz) 並開放 HTTP 下載 |
| **Warm-start 支援** | 基本權重載入 | 支援 Seed Model、Fixed Scaler、TID 隔離儲存 |

---

## 3. 詳細差異說明

### A. 非同步任務處理與 Webhook
*   **OpenDaisy**: 使用者發送 `publish_task` 後，Master 會直接進入訓練迴圈，連線保持開啟直到數十輪訓練結束。
*   **Daisy**: 支援在 JSON 任務配置中帶入 `CALLBACK_URL`。Master 接收任務後立即回傳 `202 Accepted`，並在背景執行訓練。訓練成功、失敗或觸發 Early Stopping 後，會自動向回呼網址發送 POST 請求通知結果。

### B. 自動化 Client 管理 (Multi-tenancy Support)
*   **OpenDaisy**: 需要人工在各個節點啟動 Client 程式。
*   **Daisy**: 當 Master 收到任務時，會自動查詢 MongoDB 中的 `group_id`。對於每個發現的數據群組，Master 會自動在本地（或指定節點）拉起一個獨立的 `client.py` 程序。這使得系統能夠在收到 NWDAF 請求時，自動動態地建立聯邦學習拓撲。

### C. 5G 流量數據接入與存儲
*   **Daisy 核心** 額外實作了與 5G 核心網組件 (如 UPF/EES) 對接的接口。
    *   **`/upload_data`**: 接收符合 3GPP 規範或客製化的流量統計 JSON，並自動建立索引 (`tid`, `group_id`) 存入 MongoDB。
    *   **資料隔離**: 透過 `TID` (Task ID) 實現不同訓練任務間的數據隔離。

### D. 動態模型建構與 Seed 模型
*   **動態化**: Daisy 核心可以解析任務配置中的 `MODEL_META`。例如：
    *   `input_size`: 10
    *   `num_channels`: [32, 64, 64, 64]
    *   Master 會根據這些參數直接在記憶體中建立對應的 TCN 模型，無需預先撰寫固定的模型 Class 定義。
*   **延續訓練 (Seed Support)**: 支援 `SEED_MODEL_PATH` 與 `SEED_SCALER_PATH`，允許從現有的訓練產物開始進行微調 (Fine-tuning)，而非從頭訓練。

### E. 自動化產物發佈流程
*   **OpenDaisy**: 訓練結果散落在 `model/` 資料夾下，部署時需手動搬移。
*   **Daisy**: 訓練結束後，系統會自動將權重檔 (`model.npy`)、正規化器 (`scaler.pkl`)、模型腳本 (`model.py`) 與元數據打包成壓縮檔存放在 `artifacts/` 目錄，並生成下載連結。

---

## 4. 總結

`MTLF-daisy` 版本使 Daisy 從單純的 FL 框架演進為一個專為 5G 流量預測設計的 **ML 微服務平台**，實現了從數據接入到產物部署的全自動化生命週期管理。
