#!/usr/bin/env python3

###############################################################################
#                                                                             #
# RMG - Reaction Mechanism Generator                                          #
#                                                                             #
# Copyright (c) 2002-2026 Prof. William H. Green (whgreen@mit.edu),           #
# Prof. Richard H. West (r.west@neu.edu) and the RMG Team (rmg_dev@mit.edu)   #
#                                                                             #
# Permission is hereby granted, free of charge, to any person obtaining a     #
# copy of this software and associated documentation files (the 'Software'),  #
# to deal in the Software without restriction, including without limitation   #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,    #
# and/or sell copies of the Software, and to permit persons to whom the       #
# Software is furnished to do so, subject to the following conditions:        #
#                                                                             #
# The above copyright notice and this permission notice shall be included in  #
# all copies or substantial portions of the Software.                         #
#                                                                             #
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER      #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         #
# DEALINGS IN THE SOFTWARE.                                                   #
#                                                                             #
###############################################################################

import atexit
import http.client
import json
import logging
import socket
import subprocess
import threading
from pathlib import Path


logger = logging.getLogger(__name__)


def container_name_for_image(image: str) -> str:
    """
    Deterministic, Docker-safe container name from an image name.
    "myorg/model:latest"  →  "rmg_ext_myorg_model_latest"

    A second load() call will reuse the already-running container.
    """
    safe = (
        image
        .replace("/", "_")
        .replace(":", "_")
        .replace(".", "_")
        .replace("-", "_")
    )
    return f"rmg_ext_{safe}"


def remove_container_if_exists(container_name: str) -> None:
    subprocess.run(
        ["docker", "rm", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def inspect_container(container_name: str) -> dict | None:
    try:
        raw = subprocess.check_output(
            ["docker", "inspect", container_name],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(raw)
        return data[0] if data else None
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
        return None


def get_running_container_port(container_name: str) -> int | None:
    info = inspect_container(container_name)
    if info is None:
        return None
    if info.get("State", {}).get("Status") != "running":
        return None
    ports = info.get("NetworkSettings", {}).get("Ports", {})
    for bindings in ports.values():
        if bindings:
            return int(bindings[0]["HostPort"])
    return None


def load_image_if_missing(image: str, path: Path) -> None:
    result = subprocess.run(
        ["docker", "images", "-q", image],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        logger.debug(f"Image '{image}' not found locally, loading...")
        subprocess.run(
            ["docker", "load", "-i", path / "docker_image.tar"],
            check=True
        )


class DockerHTTPClient:
    def __init__(self, path: str, image: str, container_port: int, kwargs: dict):
        self.kwargs = kwargs
        self.container_name = container_name_for_image(image)

        load_image_if_missing(image, path)

        existing_port = get_running_container_port(self.container_name)
        if existing_port is not None:
            logger.info(
                "Reusing running container '%s' on host port %d",
                self.container_name, existing_port,
            )
            host_port = existing_port
            self._cleanup_container_on_exit = False
        else:
            remove_container_if_exists(self.container_name)
            host_port = find_free_port()
            logger.info(
                "Starting container '%s' (image=%s) — host port %d → container port %d",
                self.container_name, image, host_port, container_port,
            )
            subprocess.run([
                "docker", "run", "--detach",
                "--publish", f"{host_port}:{container_port}",
                "--name", self.container_name,
                "--pull", "never",
                image,
            ], check=True)
            self._cleanup_container_on_exit = True

        host = "127.0.0.1"
        self.connection = http.client.HTTPConnection(host, host_port)  # no timeout
        self._lock = threading.RLock()
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        self.connection.close()
        if self._cleanup_container_on_exit:
            subprocess.run(
                ["docker", "rm", "--force", self.container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def post(self, endpoint: str, payload: dict) -> dict:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        with self._lock:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Connection": "keep-alive",
                    "Content-Length": str(len(body)),
                }

                self.connection.request("POST", path, body=body, headers=headers)
                resp = self.connection.getresponse()
                raw = resp.read()

                if resp.status >= 400:
                    msg = raw.decode("utf-8", errors="replace")
                    raise RuntimeError(f"HTTP {resp.status} POST {path}: {msg}")

                if not raw:
                    return {}

                return json.loads(raw.decode("utf-8"))
            except Exception as e:
                self.connection.close()
                raise RuntimeError(f"Connection error POST {path}: {e}") from e