# data_preprocessing.py - Data preparation
import pandas as pd
from sklearn.preprocessing import StandardScaler


def prepare_trading_features(df):
    """Convert raw trading data into ML features."""
    features = pd.DataFrame()

    # Time-based features
    features["hour"] = pd.to_datetime(df["Fill Time"]).dt.hour
    features["weekday"] = pd.to_datetime(df["Fill Time"]).dt.dayofweek

    # Price features
    features["price"] = df["avgPrice"]
    features["price_diff"] = df["avgPrice"] - df["Limit Price"]

    # Volume features
    features["volume"] = df["filledQty"]
    features["fill_ratio"] = df["filledQty"] / df["Quantity"]

    return features


def create_labels(df):
    """Create target labels for training."""
    # Example: 1 if trade was profitable, 0 if not
    return (df["avgPrice"] > df["Limit Price"]).astype(int)
