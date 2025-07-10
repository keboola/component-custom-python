import logging
import shutil
import subprocess
import sys
import time
from glob import glob

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


if len(sys.argv) > 1:
    data_dir = sys.argv[1]
else:
    data_dir = "./data"


subprocess.run("docker build -t cp .", shell=True, check=True)

all_passed = True
results = []

for i in range(1, 9):
    config_files = glob(f"tests/config-{i}*.json")
    if not config_files:
        continue

    filename = config_files[0]
    logging.info(f"👉 Testing {filename}...")

    shutil.copy(filename, f"{data_dir}/config.json")

    start_time = time.time()
    result = subprocess.run(["docker", "run", "-v", f"{data_dir}:/data", "-u", "1000:1000", "-it", "--rm", "cp:latest"])
    elapsed_ms = round((time.time() - start_time) * 1000)

    if result.returncode == 0:
        results.append(f"✅ {filename}: PASSED ({elapsed_ms} ms)")
    else:
        all_passed = False
        msg = f"❌ {filename}: FAILED ({elapsed_ms} ms)"
        results.append(msg)
        logging.info(msg)

    shutil.rmtree("data/.venv", ignore_errors=True)

logging.info("Results:\n" + "\n".join(f"- {r}" for r in results))

if all_passed:
    logging.info("✅ All tests passed! 🎉")
else:
    sys.exit(1)
