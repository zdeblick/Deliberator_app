import torch
import torch.nn as nn
import torch.optim as optim
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

@dataclass
class ModelData:
    rating_labels: Optional[torch.FloatTensor]
    user_indexes: Optional[torch.IntTensor]
    statement_indexes: Optional[torch.IntTensor]

class MatrixFactorization(nn.Module):
    def __init__(self, n_users, n_statements, n_factors=1, init_params=None):
        super().__init__()
        # Initialize user and statement embedding matrices
        self.user_factors = nn.Embedding(n_users, n_factors)
        self.statement_factors = nn.Embedding(n_statements, n_factors)
        
        # Initialize offset terms
        self.user_offsets = nn.Embedding(n_users, 1)
        self.statement_offsets = nn.Embedding(n_statements, 1)
        
        # Initialize with small random values
        torch.nn.init.xavier_uniform_(self.user_factors.weight)
        torch.nn.init.xavier_uniform_(self.statement_factors.weight)
        self.user_offsets.weight.data.fill_(0.0)
        self.statement_offsets.weight.data.fill_(0.0)
        self.global_offset = torch.nn.parameter.Parameter(torch.zeros(1, 1, dtype=torch.float32))

        if init_params is not None:
            if 'user_factors' in init_params:
                self.user_factors.weight.data = init_params['user_factors']
            if 'statement_factors' in init_params:
                self.statement_factors.weight.data = init_params['statement_factors']
            if 'user_offsets' in init_params:
                self.user_offsets.weight.data = init_params['user_offsets']
            if 'statement_offsets' in init_params:
                self.statement_offsets.weight.data = init_params['statement_offsets']
            if 'global_offset' in init_params:
                self.global_offset.data = init_params['global_offset']

#         self.criterion = nn.BCEWithLogitsLoss()
        self.criterion = nn.MSELoss()
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    def forward(self, data: ModelData):
        # Get embeddings for users and statements
        user_embedding = self.user_factors(data.user_indexes)
        statement_embedding = self.statement_factors(data.statement_indexes)
        
        # Get offset terms
        user_offset = self.user_offsets(data.user_indexes).squeeze()
        statement_offset = self.statement_offsets(data.statement_indexes).squeeze()
        
        # Compute prediction: global + user_offset + statement_offset + dot_product
        dot_product = (user_embedding * statement_embedding).sum(dim=-1)
        return (self.global_offset + user_offset + statement_offset + dot_product).squeeze()

def train_matrix_factorization(rating_labels, user_indexes, statement_indexes, n_factors=1, lr=0.01, n_epochs=100, 
                             reg_factors=0.01, reg_offsets=0.001):
    """
    Train matrix factorization model with offsets using ModelData format
    
    Args:
        rating_labels,
        user_indexes, 
        statement_indexes,
        n_factors: number of latent factors
        lr: learning rate
        n_epochs: number of training epochs
        reg_factors: regularization strength for factors
        reg_offsets: regularization strength for offset terms
    """
    
    n_users = np.max(user_indexes)+1
    n_statements = np.max(statement_indexes)+1
                                 
    # Initialize model
    model = MatrixFactorization(n_users, n_statements, n_factors)
    data = ModelData(torch.FloatTensor(rating_labels).squeeze().to(model.device), 
                           torch.IntTensor(user_indexes).squeeze().to(model.device),
                           torch.IntTensor(statement_indexes).squeeze().to(model.device))
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # Training loop
    losses = []
    
    for epoch in range(n_epochs):
        optimizer.zero_grad()
        
        # Forward pass using ModelData
        predictions = model(data)
        
        # Compute loss
        error_loss = model.criterion(predictions, data.rating_labels)
        
        # Add regularization terms
        factor_reg = (reg_factors * (
            (model.user_factors.weight**2).mean() + 
            (model.statement_factors.weight**2).mean()
        ))
        
        offset_reg = (reg_offsets * (
            (model.user_offsets.weight**2).mean()
            + (model.statement_offsets.weight**2).mean()
#            + model.global_offset**2
        ))
        
        total_loss = error_loss + factor_reg + offset_reg
        # Backward pass
        total_loss.backward()
        optimizer.step()
        
        losses.append(total_loss.item())
        
        if epoch % 20 == 0:
            print(f'Epoch {epoch}, Loss: {total_loss.item():.4f} '
                  f'(error: {error_loss.item():.4f}, Factor Reg: {factor_reg.item():.4f}, '
                  f'Offset Reg: {offset_reg.item():.4f})')
    
    return model, losses
