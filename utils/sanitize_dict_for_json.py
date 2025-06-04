import math
import pandas as pd
from typing import Dict, Any

def sanitize_dict_for_json(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recorre un diccionario y convierte los valores float NaN y pd.NA a None.
    """
    sanitized_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, float) and math.isnan(value):
            sanitized_dict[key] = None
        elif pd.isna(value): # pd.isna() maneja None, np.nan, pd.NaT, pd.NA
            sanitized_dict[key] = None
        else:
            sanitized_dict[key] = value
    return sanitized_dict