import pandas as pd
import numpy as np

def preprocess(df):
    """
    Prepares banking data for the AI model by isolating only 
    numeric features and removing any ground-truth labels.
    """
    # 1. Keep only numeric columns
    features = df.select_dtypes(include=[np.number]).copy()
    
    # 2. DROPPING THE 'LABEL' (Crucial for the ValueError)
    # We drop 'label' because the model wasn't trained with it.
    if 'label' in features.columns:
        features = features.drop(columns=['label'])
        
    # 3. Handle any NaN values just in case
    features = features.fillna(features.median())
    
    return features