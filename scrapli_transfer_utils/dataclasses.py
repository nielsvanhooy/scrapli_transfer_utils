from dataclasses import dataclass
from typing import TypedDict

from asyncssh import SSHClientConnectionOptions


@dataclass()
class FileCheckResult:
    """
    hash - hash value string (empty on error)

    size - size in bytes

    free - free space in bytes (0 on error)
    """

    hash: str
    size: int
    free: int


@dataclass()
class FileTransferResult:
    """
    exists - True if destination existed or created
    transferred - True if file was transferred
    verified - True if files are identical (hashes match)
    """

    exists: bool
    transferred: bool
    verified: bool


@dataclass()
class SCPConnectionParameterType(TypedDict):
    """
    Collection of authentication data needed to open a second SCP connection to the device.
    username: SSH username
    password: SSH password
    host: SSH host
    port: SSH port
    options: current SSH connection options
    """

    username: str
    password: str
    host: str
    port: int
    options: SSHClientConnectionOptions


@dataclass()
class SFTPConnectionParameterType(TypedDict):
    """
    Collection of authentication data needed to open a SFTP connection to the device.
    username: SSH username
    password: SSH password
    host: SSH host
    port: SSH port
    options: current SSH connection options
    """
