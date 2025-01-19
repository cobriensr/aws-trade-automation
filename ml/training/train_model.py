import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from datetime import datetime

class TradingDataset(Dataset):
    def __init__(self, features, targets):
        self.features = torch.FloatTensor(features)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]

class TradingModel(nn.Module):
    def __init__(self, input_size):
        super(TradingModel, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        return self.layers(x)

def prepare_data(orders_df):
    """Prepare features from trading data"""
    features = []
    
    # Time-based features
    fill_times = pd.to_datetime(orders_df['Fill Time'])
    features.append(fill_times.dt.hour.values.reshape(-1, 1))  # Hour of day
    features.append(fill_times.dt.dayofweek.values.reshape(-1, 1))  # Day of week
    
    # Price features
    features.append(orders_df['avgPrice'].values.reshape(-1, 1))
    features.append(orders_df['Limit Price'].fillna(0).values.reshape(-1, 1))
    features.append(orders_df['Stop Price'].fillna(0).values.reshape(-1, 1))
    
    # Volume features
    features.append(orders_df['filledQty'].values.reshape(-1, 1))
    features.append(orders_df['Quantity'].values.reshape(-1, 1))
    
    # Combine all features
    X = np.hstack(features)
    
    # Create target (example: 1 if profitable, 0 if not)
    # You'll want to modify this based on your strategy
    y = (orders_df['avgPrice'] > orders_df['Limit Price']).astype(int).values
    
    return X, y

def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs, device):
    """Train the model using GPU acceleration"""
    train_losses = []
    val_losses = []
    
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        total_train_loss = 0
        for features, targets in train_loader:
            features, targets = features.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, targets.unsqueeze(1))
            loss.backward()
            optimizer.step()
            
            total_train_loss += loss.item()
        
        # Validation phase
        model.eval()
        total_val_loss = 0
        with torch.no_grad():
            for features, targets in val_loader:
                features, targets = features.to(device), targets.to(device)
                outputs = model(features)
                loss = criterion(outputs, targets.unsqueeze(1))
                total_val_loss += loss.item()
        
        # Record losses
        avg_train_loss = total_train_loss / len(train_loader)
        avg_val_loss = total_val_loss / len(val_loader)
        train_losses.append(avg_train_loss)
        val_losses.append(avg_val_loss)
        
        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{num_epochs}]')
            print(f'Training Loss: {avg_train_loss:.4f}')
            print(f'Validation Loss: {avg_val_loss:.4f}')
            print('-' * 50)
    
    return train_losses, val_losses

def main():
    # Check for GPU availability
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    if device.type == 'cuda':
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory Available: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Load data
    orders_df = pd.read_csv('Orders.csv')
    
    # Prepare features and target
    X, y = prepare_data(orders_df)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Create datasets and dataloaders
    train_dataset = TradingDataset(X_train_scaled, y_train)
    test_dataset = TradingDataset(X_test_scaled, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=64)
    
    # Initialize model
    model = TradingModel(input_size=X_train.shape[1]).to(device)
    
    # Training parameters
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    num_epochs = 100
    
    # Train model
    train_losses, val_losses = train_model(
        model, train_loader, test_loader, 
        criterion, optimizer, num_epochs, device
    )
    
    # Save model
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scaler': scaler,
        'input_size': X_train.shape[1]
    }, 'trading_model.pth')
    
    # Plot training results
    plt.figure(figsize=(10, 6))
    plt.plot(train_losses, label='Training Loss')
    plt.plot(val_losses, label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss')
    plt.legend()
    plt.savefig('training_results.png')
    plt.close()

if __name__ == "__main__":
    main()