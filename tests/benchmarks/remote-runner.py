import yaml
import pathlib
from python_terraform import Terraform
import argparse
import os
import logging

from common import (
    setupRemoteEnviroment,
    spinUpRemoteRedis,
    setupRemoteBenchmark,
    runRemoteBenchmark,
    extract_git_vars,
)

# logging settings
logging.basicConfig(    
    format="%(asctime)s %(levelname)-4s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# internal aux vars
github_repo_name, github_sha, github_actor = extract_git_vars()
redisbenchmark_go_link = "https://s3.amazonaws.com/benchmarks.redislabs/redisgraph/redisgraph-benchmark-go/unstable/redisgraph-benchmark-go_linux_amd64"
private_key = "/home/filipe/.ssh/perf-cto-joint-tasks.pem"
remote_dataset_file = "/tmp/dump.rdb"
remote_module_file = "/tmp/redisgraph.so"
local_results_file = "./benchmark-result.json"
remote_results_file = "/tmp/benchmark-result.json"

parser = argparse.ArgumentParser(
    description="RedisGraph remote performance tester.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("--github_actor", type=str, default=github_actor)
parser.add_argument("--github_repo", type=str, default=github_repo_name)
parser.add_argument("--github_sha", type=str, default=github_sha)
parser.add_argument("--redis_module", type=str, default="RedisGraph")
parser.add_argument("--module_path", type=str, default="./../../src/redisgraph.so")
parser.add_argument("--setup_name_sufix", type=str, default="")
args = parser.parse_args()

tf_github_actor = args.github_actor
tf_github_repo = args.github_repo
tf_github_sha = args.github_sha
tf_redis_module = args.redis_module
tf_setup_name_sufix = "{}-{}".format(args.setup_name_sufix, tf_github_sha)
local_module_file = args.module_path

if os.getenv("EC2_ACCESS_KEY", None) is None:
    logging.error("missing required EC2_ACCESS_KEY env variable")
    exit(1)
if os.getenv("EC2_PRIVATE_PEM", None) is None:
    logging.error("missing required EC2_PRIVATE_PEM env variable")
    exit(1)
if os.getenv("EC2_REGION", None) is None:
    logging.error("missing required EC2_REGION env variable")
    exit(1)
if os.getenv("EC2_SECRET_KEY", None) is None:
    logging.error("missing required EC2_SECRET_KEY env variable")
    exit(1)

logging.info("Using the following vars on terraform deployment:")
logging.info("\tgithub_actor: {}".format(tf_github_actor))
logging.info("\tgithub_repo: {}".format(tf_github_repo))
logging.info("\tgithub_sha: {}".format(tf_github_sha))
logging.info("\tredis_module: {}".format(tf_redis_module))
logging.info("\tsetup_name sufix: {}".format(tf_setup_name_sufix))

# iterate over each benchmark file in folder
files = pathlib.Path().glob("*.yml")
remote_benchmark_setups = pathlib.Path().glob("./aws/tf-*")

for f in files:
    with open(f, "r") as stream:
        benchmark_config = yaml.safe_load(stream)
        if "ci" in benchmark_config and "terraform" in benchmark_config["ci"]:
            for remote_setup in benchmark_config["ci"]["terraform"]:
                # setup Infra
                logging.info(
                    "Deploying test defined in {} on AWS using {}".format(f, remote_setup)
                )
                tf_setup_name = "{}{}".format(remote_setup, tf_setup_name_sufix)
                logging.info("Using full setup name: {}".format(tf_setup_name))
                tf = Terraform(working_dir=remote_setup)
                (
                    return_code,
                    username,
                    server_private_ip,
                    server_public_ip,
                    server_plaintext_port,
                    client_private_ip,
                    client_public_ip,
                ) = setupRemoteEnviroment(
                    tf,
                    tf_github_sha,
                    tf_github_actor,
                    tf_setup_name,
                    tf_github_repo,
                    tf_redis_module,
                )

                # setup RedisGraph
                spinUpRemoteRedis(
                    benchmark_config,
                    server_public_ip,
                    username,
                    private_key,
                    local_module_file,
                    remote_module_file,
                    remote_dataset_file,
                )

                # setup the benchmark
                setupRemoteBenchmark(
                    client_public_ip, username, private_key, redisbenchmark_go_link
                )

                # run the benchmark
                runRemoteBenchmark(
                    client_public_ip, username, private_key,server_private_ip, server_plaintext_port, benchmark_config, remote_results_file, local_results_file
                )

                # tear-down
                logging.info("Tearing down setup")
                tf_output = tf.destroy()
                logging.info("Tear-down completed")