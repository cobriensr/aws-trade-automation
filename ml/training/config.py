# config.py - Training configuration
class TrainingConfig:
    # Model parameters
    INPUT_FEATURES = ['hour', 'weekday', 'price', 'volume', 'filled_qty']
    HIDDEN_LAYERS = [256, 128, 64]
    DROPOUT_RATE = 0.2
    
    # Training parameters
    BATCH_SIZE = 64
    LEARNING_RATE = 0.001
    NUM_EPOCHS = 100
    TRAIN_TEST_SPLIT = 0.2
    
    # Paths
    DATA_PATH = '../data/Orders.csv'
    MODEL_SAVE_PATH = '../models/trading_model.pth'
    
    # Trading specific
    MIN_CONFIDENCE = 0.7
    PROFIT_THRESHOLD = 0.02  # 2% profit target