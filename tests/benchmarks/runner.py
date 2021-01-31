import yaml
import pathlib
import subprocess

redisgraph_benchmark = "/Users/roilipman/go/src/github.com/filipecosta90/redisgraph-benchmark-go/redisgraph-benchmark-go"

# iterate over each benchmark file in folder
files = pathlib.Path().glob("*.yml")
for f in files:
    with open(f, 'r') as stream:
        data = yaml.safe_load(stream)

        # TODO: load dataset
        dataset = data['dataset']

        cmd = redisgraph_benchmark + " "
        cmd += "-h %s " % data['host']
        cmd += "-p %d " % data['port']
        cmd += "-c %d " % data['clients']
        cmd += "-graph-key %s " % data["graph"]
        cmd += "-rps %d " % data["RPS"]

        if data["requests"] == -1:
            cmd += "-l "
        else:
            cmd += "-n %d " % data["requests"]

        cmd += "\"" + data["queries"][0]["q"] + "\""

        # expectations
        expected_latency = data["expectations"]["avg_latency"]
        expected_throughput = data["expectations"]["throughput"]

        print(cmd)
        #process = subprocess.Popen(cmd.split())

