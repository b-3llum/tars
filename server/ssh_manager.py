"""SSH manager — paramiko-based, key-auth only, restricted to configured hosts."""

from __future__ import annotations

import paramiko

from .config import get_hosts_config
from .logger import audit, get_logger

log = get_logger()


class SSHError(Exception):
    pass


def get_host(name: str) -> dict:
    """Retrieve a host config by name."""
    hosts = get_hosts_config()
    if name not in hosts:
        raise SSHError(f"Unknown host: {name}. Available: {list(hosts.keys())}")
    return hosts[name]


def execute_on_host(host_name: str, command: str, timeout: int = 30) -> str:
    """Execute a command on a preconfigured host via SSH.

    - Key-based auth only (no passwords).
    - Command must be from the whitelist (enforced by action_engine before calling).
    """
    host = get_host(host_name)

    audit(
        "ssh_execute",
        intent="ssh_command",
        target=f"{host['user']}@{host['ip']}",
        detail=command,
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())

    try:
        key = paramiko.RSAKey.from_private_key_file(host["key_path"])
        client.connect(
            hostname=host["ip"],
            username=host["user"],
            pkey=key,
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
        )

        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        if exit_code != 0:
            log.warning("SSH command exited %d on %s: %s", exit_code, host_name, err)
            return f"[exit {exit_code}]\n{out}\n{err}".strip()

        return out.strip()

    except paramiko.AuthenticationException:
        raise SSHError(f"Authentication failed for {host_name}")
    except paramiko.SSHException as e:
        raise SSHError(f"SSH error on {host_name}: {e}")
    except Exception as e:
        raise SSHError(f"Connection to {host_name} failed: {e}")
    finally:
        client.close()
