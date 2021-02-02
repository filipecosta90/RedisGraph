import yaml
import pathlib
from python_terraform import Terraform
import argparse
from git import Repo
import os
import logging

from common import copyFileToRemoteSetup, executeRemoteCommands, getFileFromRemoteSetup

github_repo = Repo("{}/../..".format(os.getcwd()))
github_repo_name = github_repo.remotes[0].config_reader.get("url")
github_sha = github_repo.head.object.hexsha
github_actor = github_repo.config_reader().get_value("user", "name")
redisbenchmark_go_link = "https://s3.amazonaws.com/benchmarks.redislabs/redisgraph/redisgraph-benchmark-go/unstable/redisgraph-benchmark-go_linux_amd64"

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

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
        for remote_setup in benchmark_config["ci"]["terraform"]:
            logging.info(
                "Deploying test defined in {} on AWS using {}".format(f, remote_setup)
            )
            tf_setup_name = "{}{}".format(remote_setup, tf_setup_name_sufix)
            logging.info("Using full setup name: {}".format(tf_setup_name))
            tf = Terraform(working_dir=remote_setup)
            return_code, stdout, stderr = tf.init(capture_output=True)
            return_code, stdout, stderr = tf.refresh()
            tf_output = tf.output()
            server_private_ip = tf_output["server_private_ip"]["value"][0]
            server_public_ip = tf_output["server_public_ip"]["value"][0]
            client_private_ip = tf_output["client_private_ip"]["value"][0]
            client_public_ip = tf_output["client_public_ip"]["value"][0]
            if (
                server_private_ip is not None
                or server_public_ip is not None
                or client_private_ip is not None
                or client_public_ip is not None
            ):
                logging.warning("Destroying previous setup")
                tf.destroy()
            return_code, stdout, stderr = tf.apply(
                skip_plan=True,
                capture_output=False,
                refresh=True,
                var={
                    "github_sha": tf_github_sha,
                    "github_actor": tf_github_actor,
                    "setup_name": tf_setup_name,
                    "github_repo": tf_github_repo,
                    "redis_module": tf_redis_module,
                },
            )
            tf_output = tf.output()
            server_private_ip = tf_output["server_private_ip"]["value"][0]
            server_public_ip = tf_output["server_public_ip"]["value"][0]
            server_plaintext_port = 6379
            client_private_ip = tf_output["client_private_ip"]["value"][0]
            client_public_ip = tf_output["client_public_ip"]["value"][0]

            # copy the rdb to DB machine
            dataset = None
            username = "ubuntu"
            remote_dataset_file = "/tmp/dump.rdb"
            remote_module_file = "/tmp/redisgraph.so"
            private_key = "/home/filipe/.ssh/perf-cto-joint-tasks.pem"
            for k in benchmark_config["dbconfig"]:
                if "dataset" in k:
                    dataset = k["dataset"]
            if dataset is not None:
                copyFileToRemoteSetup(
                    server_public_ip,
                    username,
                    private_key,
                    dataset,
                    remote_dataset_file,
                )

            # copy the module to the DB machine
            copyFileToRemoteSetup(
                server_public_ip,
                username,
                private_key,
                local_module_file,
                remote_module_file,
            )
            executeRemoteCommands(
                server_public_ip,
                username,
                private_key,
                ["chmod 755 {}".format(remote_module_file)],
            )

            # start redis-server
            commands = [
                "redis-server --dir /tmp/ --daemonize yes --protected-mode no --loadmodule {}".format(
                    remote_module_file
                )
            ]
            executeRemoteCommands(server_public_ip, username, private_key, commands)

            # setup the benchmark
            commands = [
                "wget {} -q -O /tmp/redisgraph-benchmark-go".format(
                    redisbenchmark_go_link
                ),
                "chmod 755 /tmp/redisgraph-benchmark-go",
            ]
            executeRemoteCommands(client_public_ip, username, private_key, commands)

            # run the benchmark
            queries_str = ""
            for k in benchmark_config["queries"]:
                query = k["q"]
                queries_str += ' -query "{}"'.format(query)
                if "ratio" in k:
                    queries_str += " -query-ratio {}".format(k["ratio"])

            for k in benchmark_config["clientconfig"]:
                if "graph" in k:
                    queries_str += " -graph-key {}".format(k["graph"])
                if "clients" in k:
                    queries_str += " -c {}".format(k["clients"])
                if "requests" in k:
                    queries_str += " -n {}".format(k["requests"])
                if "rps" in k:
                    queries_str += " -rps {}".format(k["rps"])
            queries_str += " -h {}".format(server_private_ip)
            queries_str += " -p {}".format(server_plaintext_port)
            results_file = "/tmp/benchmark-result.json"
            queries_str += " -json-out-file {}".format(results_file)

            logging.info(queries_str)

            logging.info("Running the benchmark")
            commands = ["/tmp/redisgraph-benchmark-go {}".format(queries_str)]
            executeRemoteCommands(client_public_ip, username, private_key, commands)

            logging.info("Extracting the benchmark results")
            getFileFromRemoteSetup(
                client_public_ip,
                username,
                private_key,
                "./benchmark-result.json",
                results_file,
            )

            # tear-down
            logging.info("Tearing down setup")
            tf_output = tf.destroy()
            logging.info("Tear-down completed")
