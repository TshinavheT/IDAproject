"""
Model definitions shared by Q3-Q7.

Every model is a full Pipeline: the Q2.4 preprocessor (fit on training rows only)
followed by the classifier. Fitting the whole pipeline on the training split means
imputation medians, scaling factors and one-hot categories are learned from
2018-2021 only, and the same object can be saved and loaded by the app.
"""

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from neural import TorchTabularClassifier
from pipeline_q24 import build_pipeline

SEED = 42


class PriorOutcomeRule(BaseEstimator, ClassifierMixin):
    """Persistence baseline: predict that year t+1 repeats the year-t audit outcome.

    Works on the raw feature frame (no preprocessing). It learns nothing, so it shows
    how much of the models' skill comes from audit history alone.
    """

    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict(self, X):
        return (X["prior_audit_outcome"] == "at_risk").astype(int).to_numpy()

    def predict_proba(self, X):
        p = self.predict(X).astype(float)
        return np.column_stack([1 - p, p])


def make_pipeline(classifier):
    return Pipeline([("preprocess", build_pipeline()), ("model", classifier)])


BASELINES = ["Baseline (Dummy)", "Baseline (Repeat last year)"]


def build_models():
    return {
        "Baseline (Dummy)": make_pipeline(
            DummyClassifier(strategy="most_frequent")),
        "Baseline (Repeat last year)": PriorOutcomeRule(),
        "Logistic Regression": make_pipeline(
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
        "Random Forest": make_pipeline(
            RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=SEED, n_jobs=-1)),
        "MLP": make_pipeline(
            TorchTabularClassifier(arch="mlp", hidden=(64, 32), dropout=0.2,
                                   lr=1e-3, batch_size=32, max_epochs=100,
                                   patience=10, random_state=SEED)),
        "Residual Tabular NN": make_pipeline(
            TorchTabularClassifier(arch="resnet", width=64, n_blocks=1, dropout=0.2,
                                   lr=1e-3, weight_decay=1e-4, batch_size=32,
                                   max_epochs=100, patience=10, random_state=SEED)),
    }
