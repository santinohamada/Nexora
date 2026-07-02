import torch
import torch.nn as nn

class SignLanguageLSTM(nn.Module):
    def __init__(self, num_classes, input_size=300, hidden_size=128, num_layers=2, dropout=0.2):
        super(SignLanguageLSTM, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc1 = nn.Linear(hidden_size, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(64, num_classes)
        
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        
        # LSTM output
        out, (hn, cn) = self.lstm(x)
        
        # We only need the output from the last time step
        # out shape: (batch, seq_len, hidden_size)
        # Get the last sequence step
        last_out = out[:, -1, :]
        
        # Fully connected layers
        x = self.fc1(last_out)
        x = self.relu(x)
        x = self.dropout(x)
        out = self.fc2(x)
        
        return out
