import paramiko

class SSHExecutor:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def run_command(self, command):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.host, port=self.port, username=self.user, password=self.password)
        try:
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            return output, error
        finally:
            client.close()

    def upload_file(self, local_path, remote_path):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.host, port=self.port, username=self.user, password=self.password)
        try:
            sftp = client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return True
        finally:
            client.close()