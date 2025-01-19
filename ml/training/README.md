# Trading Automation ML Component

Machine learning addition to the existing AWS trading automation system. This component analyzes historical trade data to predict trade outcomes and enhance decision-making.

## Overview

This ML pipeline integrates with the existing trading automation system by:

1. Training on historical trade data from Tradovate
2. Predicting potential trade outcomes
3. Providing confidence scores for trading decisions

## Setup

### Requirements

- Python 3.8+
- CUDA-capable GPU (RTX 4080 Super)
- 16GB+ RAM

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix/MacOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r src/ml/training/requirements.txt
```

## Project Structure

``` bash
src/ml/
├── training/              # Training scripts
│   ├── train_model.py    # Main training script
│   ├── model_definition.py
│   ├── data_preprocessing.py
│   ├── utils.py
│   ├── config.py
│   └── requirements.txt
├── models/               # Saved models (DVC tracked)
│   └── .gitignore
├── notebooks/           # Development notebooks
│   └── model_development.ipynb
└── data/               # Training data
    ├── raw/           # Original trade data
    └── processed/     # Processed features
```

## Development Workflow

1. Data Preparation

```python
# Load and preprocess trade data
python data_preprocessing.py
```

1. Model Training

```python
# Train the model
python train_model.py
```

1. Model Versioning

```bash
# Track new model version
dvc add src/ml/models/trading_model.pth
dvc push
```

## Model Details

- Architecture: Neural Network
- Input Features:
  - Time-based (hour, weekday)
  - Price data
  - Volume information
  - Trade-specific features
- Output: Trade success probability

## Integration

The model integrates with the existing Lambda function by:

1. Loading the trained model
2. Processing incoming trade signals
3. Adding prediction confidence to trade decisions

## Monitoring

Model performance metrics are tracked using:

- Training/validation loss
- Prediction accuracy
- Trading-specific metrics (profit factor, win rate)

## Future Improvements

- Feature engineering for technical indicators
- Hyperparameter optimization
- Real-time model updating
- A/B testing framework

## Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Submit pull request

## Notes

- Model files are tracked with DVC, not Git
- Requires GPU for optimal training performance
- Regular retraining recommended with new data
