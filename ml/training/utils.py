# utils.py - Helper functions
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score


def calculate_metrics(y_true, y_pred):
    """Calculate trading-specific metrics."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "profit_factor": calculate_profit_factor(y_true, y_pred),
    }


def calculate_profit_factor(y_true, y_pred, returns):
    """Calculate the profit factor of predictions."""
    correct_trades = returns[y_true == y_pred]
    winning_trades = correct_trades[correct_trades > 0].sum()
    losing_trades = abs(correct_trades[correct_trades < 0].sum())
    return winning_trades / losing_trades if losing_trades != 0 else float("inf")


def save_checkpoint(model, optimizer, epoch, metrics, path):
    """Save model checkpoint with metadata."""
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
        },
        path,
    )
