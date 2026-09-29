import json
import os
from typing import List

cur_path = os.path.dirname(os.path.abspath(__file__))


def load_data(file_name: str) -> List:
    data = []

    with open(os.path.join(cur_path, "../seeds/datas", file_name), "r") as f:
        data = json.load(f)
    return data
