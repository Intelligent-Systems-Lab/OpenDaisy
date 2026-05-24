import os

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from daisyfl.strategy.fedavg import FedAvg
from daisyfl.common import LOSS, METRICS, TID, DATA_SAMPLES, CURRENT_ROUND

class EarlyStoppingFedAvg(FedAvg):
    def __init__(self, *args, task_config=None, **kwargs):
        cfg = task_config or {}
        kwargs.setdefault("num_clients_fit", int(cfg.get("NUM_CLIENTS_FIT", 2)))
        kwargs.setdefault("num_clients_evaluate", int(cfg.get("NUM_CLIENTS_EVALUATE", 2)))
        super().__init__(*args, **kwargs)
        self.max_es_patience = int(cfg.get("ES_PATIENCE", 5))
        self.max_lr_patience = int(cfg.get("LR_PATIENCE", 3))
        self.best_loss = float('inf')
        self.es_patience = 0
        self.lr_patience = 0
        self.current_lr = float(cfg.get("INITIAL_LR", 1e-3))
        self.use_fixed_scaler = bool(cfg.get("USE_FIXED_SCALER", False))

    def configure_fit(self, parameters, config, **kwargs):
        config["lr"] = self.current_lr
        current_round = config.get(CURRENT_ROUND, 0)
        if (not self.use_fixed_scaler) and current_round == 1:
            print("\n[NWDAF CustomStrategy] Round 1 configured as stats round (federated scaler aggregation enabled)")
            config["is_stats_round"] = True
        elif self.use_fixed_scaler and current_round == 1:
            print("\n[NWDAF CustomStrategy] Fixed scaler mode enabled: skipping stats round and training with pre-seeded scaler")
        return super().configure_fit(parameters, config, **kwargs)

    def aggregate_fit(self, results, **kwargs):
        is_stats_round = False
        if results:
            _, fit_res = results[0]
            is_stats_round = bool(fit_res.config.get("is_stats_round"))

        if not is_stats_round:
            return super().aggregate_fit(results, **kwargs)

        stats_list = []
        for _, fit_res in results:
            metrics = fit_res.config.get(METRICS, {})
            stats = metrics.get("scaler_stats")
            if stats is not None:
                stats_list.append(stats)

        if not stats_list:
            raise RuntimeError("Stats round completed without receiving scaler statistics from clients")

        total_n = sum(int(stats["n"]) for stats in stats_list)
        if total_n <= 0:
            raise RuntimeError("Stats round produced non-positive total sample count")

        num_features = len(stats_list[0]["mean"])
        global_mean = np.zeros(num_features, dtype=np.float64)
        total_ex2 = np.zeros(num_features, dtype=np.float64)
        for stats in stats_list:
            weight = float(stats["n"]) / float(total_n)
            local_mean = np.asarray(stats["mean"], dtype=np.float64)
            local_var = np.asarray(stats["var"], dtype=np.float64)
            global_mean += local_mean * weight
            total_ex2 += (local_var + np.square(local_mean)) * weight

        global_var = np.maximum(total_ex2 - np.square(global_mean), 0.0)
        global_scaler = StandardScaler()
        global_scaler.mean_ = global_mean
        global_scaler.var_ = global_var
        global_scaler.scale_ = np.where(global_var > 0.0, np.sqrt(global_var), 1.0)
        global_scaler.n_samples_seen_ = int(total_n)

        _, fit_res = results[0]
        tid = fit_res.config.get(TID)
        scaler_dir = os.path.join("model", tid) if tid else "model"
        scaler_path = os.path.join(scaler_dir, "scaler.pkl")
        os.makedirs(scaler_dir, exist_ok=True)
        joblib.dump(global_scaler, scaler_path)

        print(
            f"\n[NWDAF CustomStrategy] Stats round complete: clients={len(stats_list)} "
            f"global_n={total_n} scaler={scaler_path}"
        )

        return fit_res.parameters, {DATA_SAMPLES: total_n}

    def aggregate_evaluate(self, results, **kwargs):
        metrics = super().aggregate_evaluate(results, **kwargs)
        if metrics is None or LOSS not in metrics:
            return metrics

        if results:
            _, evaluate_res = results[0]
            if evaluate_res.config.get("is_stats_round"):
                print("\n[NWDAF CustomStrategy] Skipping early-stopping update for stats round")
                return metrics

        val_loss = metrics[LOSS]
        print(f"\n[NWDAF CustomStrategy] Round Validation Loss: {val_loss:.4f} | Current LR: {self.current_lr}")

        if val_loss < self.best_loss:
            self.best_loss = val_loss
            self.es_patience = 0
            self.lr_patience = 0
        else:
            self.es_patience += 1
            self.lr_patience += 1
            print(f"[NWDAF CustomStrategy] Val Loss did not improve. "
                  f"ES Patience: {self.es_patience}/{self.max_es_patience} | "
                  f"LR Patience: {self.lr_patience}/{self.max_lr_patience}")

        # Early Stopping check
        if self.es_patience >= self.max_es_patience:
            print(f"[NWDAF CustomStrategy] Early stopping triggered! "
                  f"Validation loss plateaued for {self.max_es_patience} rounds.")
            print(f"[NWDAF CustomStrategy] Master ending current task gracefully.")
            class EarlyStoppingException(Exception):
                pass
            raise EarlyStoppingException(
                f"Validation loss plateaued for {self.max_es_patience} rounds")

        # ReduceLROnPlateau check
        if self.lr_patience >= self.max_lr_patience:
            self.current_lr *= 0.5
            self.lr_patience = 0
            print(f"[NWDAF CustomStrategy] Plateau reached. Halving Learning Rate to {self.current_lr}")

        return metrics
