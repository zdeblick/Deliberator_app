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
    def __init__(self, n_users, n_statements, n_factors=1, init_params=None, include_user_intercept=True):
        super().__init__()
        # Initialize user and statement embedding matrices
        self.user_factors = nn.Embedding(n_users, n_factors)
        self.statement_factors = nn.Embedding(n_statements, n_factors)
        
        # Initialize intercept terms
        self.user_intercepts = nn.Embedding(n_users, 1)
        self.statement_intercepts = nn.Embedding(n_statements, 1)
        
        # Initialize with small random values
        torch.nn.init.xavier_uniform_(self.user_factors.weight)
        torch.nn.init.xavier_uniform_(self.statement_factors.weight)
        self.user_intercepts.weight.data.fill_(0.0)
        if not include_user_intercept:
            self.user_intercepts.requires_grad_(False)
        self.statement_intercepts.weight.data.fill_(0.0)
        self.global_intercept = torch.nn.parameter.Parameter(torch.zeros(1, 1, dtype=torch.float32))

        if init_params is not None:
            if 'user_factors' in init_params:
                self.user_factors.weight.data = init_params['user_factors']
            if 'statement_factors' in init_params:
                self.statement_factors.weight.data = init_params['statement_factors']
            if 'user_intercepts' in init_params:
                self.user_intercepts.weight.data = init_params['user_intercepts']
            if 'statement_intercepts' in init_params:
                self.statement_intercepts.weight.data = init_params['statement_intercepts']
            if 'global_intercept' in init_params:
                self.global_intercept.data = init_params['global_intercept']

#         self.criterion = nn.BCEWithLogitsLoss()
        self.criterion = nn.MSELoss()
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    def forward(self, data: ModelData):
        # Get embeddings for users and statements        
        user_embedding = self.user_factors(data.user_indexes)
        statement_embedding = self.statement_factors(data.statement_indexes)
        
        # Get intercept terms
        user_intercept = self.user_intercepts(data.user_indexes).squeeze()
        statement_intercept = self.statement_intercepts(data.statement_indexes).squeeze()
        
        # Compute prediction: global + user_intercept + statement_intercept + dot_product
        dot_product = (user_embedding * statement_embedding).sum(dim=-1)
        return (self.global_intercept + user_intercept + statement_intercept + dot_product).squeeze()

def train_matrix_factorization(rating_labels, user_indexes, statement_indexes, n_users=None, n_statements=None, n_factors=1, lr=0.01, n_epochs=200, 
                             reg_factors=0.06, reg_intercepts=0.3, init_params=None, include_user_intercept=True):
    """
    Train matrix factorization model with intercepts using ModelData format
    
    Args:
        rating_labels,
        user_indexes, 
        statement_indexes,
        n_factors: number of latent factors
        lr: learning rate
        n_epochs: number of training epochs
        reg_factors: regularization strength for factors
        reg_intercepts: regularization strength for intercept terms
    """
    if n_users is None:
        n_users = np.max(user_indexes)+1
    if n_statements is None:
        n_statements = np.max(statement_indexes)+1
                                 
    # Initialize model
    model = MatrixFactorization(n_users, n_statements, n_factors, init_params=init_params,include_user_intercept=include_user_intercept)
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
        
        intercept_reg = (reg_intercepts * (
            (model.user_intercepts.weight**2).mean()
            + (model.statement_intercepts.weight**2).mean()
#            + model.global_intercept**2
        ))
        
        total_loss = error_loss + factor_reg + intercept_reg
        # Backward pass
        total_loss.backward()
        optimizer.step()
        
        losses.append(total_loss.item())
        
        if epoch % 20 == 0:
            print(f'Epoch {epoch}, Loss: {total_loss.item():.4f} '
                  f'(error: {error_loss.item():.4f}, Factor Reg: {factor_reg.item():.4f}, '
                  f'intercept Reg: {intercept_reg.item():.4f})')
    
    return model, losses
