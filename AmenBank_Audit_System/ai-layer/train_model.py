# train_model.py
import joblib
from src.data_loader import load_dataset
from src.preprocessing import preprocess
from src.model import train_iforest
import config

def run_training_pipeline():
    print("📂 [STAGE 1] Loading Amen Bank Infrastructure Logs...")
    df = load_dataset(config.DATA_PATH)
    
    print("🧹 [STAGE 2] Preprocessing Features for AI...")
    features = preprocess(df)
    
    print(f"🌲 [STAGE 3] Training Isolation Forest Engine...")
    model = train_iforest(features)
    
    # Save the 'Brain'
    joblib.dump(model, config.MODEL_PATH)
    print(f"✅ SUCCESS: AI Brain saved to {config.MODEL_PATH}")

if __name__ == "__main__":
    run_training_pipeline()