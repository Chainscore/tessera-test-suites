
from jam.utils.shuffle import shuffle
from jam.types.base.sequences import  decodable_vector, Vector
import json
from pathlib import Path

SHUFFLE_DIR = Path(__file__).parents[2] / "ext" / "w3f" / "shuffle"

def test_shuffle():

    # Load test vectors
    with open(SHUFFLE_DIR / "shuffle_tests.json", "r") as f:
        vectors_json = json.load(f)

        for i in range(len(vectors_json)):
            array = []
            for j in range(vectors_json[i]['input']):
                array.append(j)
            print(f"Testing vector #{i}")
            numbers = shuffle(vectors_json[i]["entropy"], array)
            assert numbers == vectors_json[i]["output"]
            print(f"✅ Passed vector #{i}")