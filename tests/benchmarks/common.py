import logging
import sys
import pysftp
import paramiko


def viewBar_no_tqdm(a, b):
    res = a / int(b) * 100
    sys.stdout.write("\r    Complete precent: %.2f %%" % (res))
    sys.stdout.flush()


def copyFileToRemoteSetup(
    server_public_ip, username, private_key, local_file, remote_file
):
    logging.info(
        "\tCopying local file {} to remote server {}".format(local_file, remote_file)
    )
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    srv = pysftp.Connection(
        host=server_public_ip, username=username, private_key=private_key, cnopts=cnopts
    )
    srv.put(local_file, remote_file, callback=viewBar_no_tqdm)
    srv.close()
    logging.info("")

def getFileFromRemoteSetup(
    server_public_ip, username, private_key, local_file, remote_file
):
    logging.info(
        "\Retrieving remote file {} from remote server {} ".format(remote_file, server_public_ip )
    )
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    srv = pysftp.Connection(
        host=server_public_ip, username=username, private_key=private_key, cnopts=cnopts
    )
    srv.get(remote_file, local_file, callback=viewBar_no_tqdm)
    srv.close()
    logging.info("")


def executeRemoteCommands(server_public_ip, username, private_key, commands):
    res = []
    k = paramiko.RSAKey.from_private_key_file(private_key)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.info("Connecting to remote server {}".format(server_public_ip))
    c.connect(hostname=server_public_ip, username=username, pkey=k)
    logging.info("Connected to remote server {}".format(server_public_ip))
    for command in commands:
        logging.info('Executing remote command "{}"'.format(command))
        stdin, stdout, stderr = c.exec_command(command)
        stdout=stdout.readlines()
        stderr=stderr.readlines()
        res.append([stdout,stderr])
    c.close()
    return res