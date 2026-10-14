"""
PyTorch tabular classifiers wrapped as scikit-learn estimators.

Wrapping the networks this way means the MLP and the residual network can sit
inside the same sklearn Pipeline as the preprocessor, exactly like Logistic
Regression and Random Forest. That gives every model identical inputs, lets
GridSearch/Optuna/ablations treat them uniformly, and lets the Streamlit app
load one saved end-to-end pipeline (Q7.2).

Early stopping uses an internal slice of the TRAINING data, never the
validation year, so the validation year stays clean for model selection.
"""

import numpy as np
import torch
from scipy import sparse
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import train_test_split
from torch import nn


class MLPNet(nn.Module):
    """Feed-forward network: input -> 64 -> 32 -> 2 (ReLU + dropout)."""

    def __init__(self, n_in, hidden=(64, 32), dropout=0.2):
        super().__init__()
        layers, prev = [], n_in
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, 2))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class ResidualNet(nn.Module):
    """Tabular residual network: input -> 64, then n_blocks of h + F(h), -> 2."""

    def __init__(self, n_in, width=64, n_blocks=1, dropout=0.2, use_skip=True):
        super().__init__()
        self.use_skip = use_skip
        self.stem = nn.Sequential(nn.Linear(n_in, width), nn.ReLU())
        self.blocks = nn.ModuleList([
            nn.Sequential(nn.Linear(width, width), nn.ReLU(), nn.Dropout(dropout))
            for _ in range(n_blocks)
        ])
        self.head = nn.Linear(width, 2)

    def forward(self, x):
        h = self.stem(x)
        for block in self.blocks:
            h = h + block(h) if self.use_skip else block(h)
        return self.head(h)


class TorchTabularClassifier(BaseEstimator, ClassifierMixin):
    """sklearn-compatible binary classifier around MLPNet / ResidualNet."""

    def __init__(self, arch="mlp", hidden=(64, 32), width=64, n_blocks=1,
                 dropout=0.2, use_skip=True, lr=1e-3, weight_decay=0.0,
                 batch_size=32, max_epochs=100, patience=10,
                 class_weight="balanced", es_fraction=0.15, random_state=42):
        self.arch = arch
        self.hidden = hidden
        self.width = width
        self.n_blocks = n_blocks
        self.dropout = dropout
        self.use_skip = use_skip
        self.lr = lr
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.class_weight = class_weight
        self.es_fraction = es_fraction
        self.random_state = random_state

    @staticmethod
    def _to_tensor(X):
        if sparse.issparse(X):
            X = X.toarray()
        return torch.as_tensor(np.asarray(X, dtype=np.float32))

    def _build(self, n_in):
        if self.arch == "mlp":
            return MLPNet(n_in, self.hidden, self.dropout)
        if self.arch == "resnet":
            return ResidualNet(n_in, self.width, self.n_blocks, self.dropout, self.use_skip)
        raise ValueError(f"Unknown arch: {self.arch}")

    def fit(self, X, y):
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        y = np.asarray(y)
        self.classes_ = np.unique(y)
        y_idx = np.searchsorted(self.classes_, y)

        X_tr, X_es, y_tr, y_es = train_test_split(
            X, y_idx, test_size=self.es_fraction, stratify=y_idx,
            random_state=self.random_state)
        X_tr, X_es = self._to_tensor(X_tr), self._to_tensor(X_es)
        y_tr, y_es = torch.as_tensor(y_tr), torch.as_tensor(y_es)

        weights = None
        if self.class_weight == "balanced":
            counts = np.bincount(y_idx, minlength=2)
            weights = torch.as_tensor(len(y_idx) / (2 * counts), dtype=torch.float32)
        loss_fn = nn.CrossEntropyLoss(weight=weights)

        self.model_ = self._build(X_tr.shape[1])
        opt = torch.optim.Adam(self.model_.parameters(), lr=self.lr,
                               weight_decay=self.weight_decay)
        gen = torch.Generator().manual_seed(self.random_state)

        self.history_ = {"train_loss": [], "es_loss": [], "train_acc": [], "es_acc": []}
        best_loss, best_state, wait = np.inf, None, 0

        for epoch in range(self.max_epochs):
            self.model_.train()
            perm = torch.randperm(len(X_tr), generator=gen)
            for i in range(0, len(X_tr), self.batch_size):
                idx = perm[i:i + self.batch_size]
                opt.zero_grad()
                loss = loss_fn(self.model_(X_tr[idx]), y_tr[idx])
                loss.backward()
                opt.step()

            self.model_.eval()
            with torch.no_grad():
                out_tr, out_es = self.model_(X_tr), self.model_(X_es)
                tr_loss = loss_fn(out_tr, y_tr).item()
                es_loss = loss_fn(out_es, y_es).item()
                self.history_["train_loss"].append(tr_loss)
                self.history_["es_loss"].append(es_loss)
                self.history_["train_acc"].append((out_tr.argmax(1) == y_tr).float().mean().item())
                self.history_["es_acc"].append((out_es.argmax(1) == y_es).float().mean().item())

            if es_loss < best_loss - 1e-4:
                best_loss, wait = es_loss, 0
                best_state = {k: v.clone() for k, v in self.model_.state_dict().items()}
                self.best_epoch_ = epoch + 1
            else:
                wait += 1
                if wait >= self.patience:
                    break

        self.n_epochs_run_ = epoch + 1
        self.model_.load_state_dict(best_state)
        self.model_.eval()
        return self

    def predict_proba(self, X):
        with torch.no_grad():
            logits = self.model_(self._to_tensor(X))
            return torch.softmax(logits, dim=1).numpy()

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(1)]
