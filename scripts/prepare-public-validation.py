import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "gpu-data"))

from src.public_validation import prepare_validation_cases


parser = argparse.ArgumentParser(description="Prepare deterministic public GPU Data validation cases")
parser.add_argument(
    "--source",
    type=Path,
    default=ROOT / "gpu-data" / "validation" / "alibaba_t4" / "source",
)
parser.add_argument(
    "--output",
    type=Path,
    default=Path(r"E:\DockerData\gpu-saas\validation\prepared\alibaba-pai-t4-azure-eastus"),
)
args = parser.parse_args()
cases = prepare_validation_cases(args.source, args.output)
for name, path in cases.items():
    print(f"{name}: {path}")
