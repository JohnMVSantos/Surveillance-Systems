# Surveillance-Systems

Creating the environment

This specific command includes already installed libraries such as picamera2.
```shell 
python -m venv --system-site-packages env
```

Install other requirements

```shell
pip install -r requirements.txt
```

Add permission to the file to allow saving in vscode from an SSH client.
```shell
sudo chmod a+rwx <Filename>
```

```shell
python -m surveillance -c config.json
```