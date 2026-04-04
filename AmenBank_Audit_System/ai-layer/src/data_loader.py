import pandas as pd

def load_dataset(path):

    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df
    import pandas as pd

def load_dataset(path):
    df = pd.read_csv(path)
    return df