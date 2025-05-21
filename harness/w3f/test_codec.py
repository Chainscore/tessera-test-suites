import json
from pathlib import Path

import pytest

from jam.types.block import Block
from jam.types.extrinsics import AssurancesExtrinsic, DisputesExtrinsic, GuaranteesExtrinsic, PreimagesExtrinsic, \
	TicketsExtrinsic
from jam.types.header import Header
from jam.types.work.item import WorkItem
from jam.types.work.package import WorkPackage
from jam.types.work.report import WorkReport, WorkResult

TV_PATH = Path(__file__).parents[2] / "ext" / "w3f" / "codec" / "data"


def fetch_vectors(fmt: str, pattern: str):
	vector_dir = TV_PATH
	return [
		(f.name, json.load(open(f)))
		for f in vector_dir.glob(f"{pattern}*.{fmt}")
	]

@pytest.mark.parametrize("pattern,cls", [
	("assurance_extrinsic", AssurancesExtrinsic),
	("disputes_extrinsic", DisputesExtrinsic),
	("guarantees_extrinsic", GuaranteesExtrinsic),
	("preimages_extrinsic", PreimagesExtrinsic),
	("tickets_extrinsic", TicketsExtrinsic),
	("header", Header),
	("block", Block),
	("work_item", WorkItem),
	("work_package", WorkPackage),
	("work_report", WorkReport),
	("work_result", WorkResult)
])
def test_codec(pattern: str, cls):
	# Process files
	for name, data in fetch_vectors("json", pattern):
		print("Processing", name, "...")
		obj = cls.from_json(data)
		binary = (open(TV_PATH / f"{name.split(".")[0]}.bin", "br")).read()
		assert obj.encode().hex() == binary.hex()
