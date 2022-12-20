import hashlib
import os
import shutil
from abc import abstractmethod, ABC
from pathlib import PurePath
from typing import Optional, Union, Literal, Callable

import aiofiles
from scrapli.driver import AsyncNetworkDriver

from scrapli_transfer_utils.dataclasses import FileCheckResult, FileTransferResult
from scrapli_transfer_utils.logging import logger


class AsyncTransferFeature(ABC):
    """
    This class extends a driver with Transfer capabilities

    You need to implement device specific methods. If your device does not support that method,
    just return a value described in the abstract methods.
    """

    def __init__(self, connection: AsyncNetworkDriver):
        # \x0C is CTRL-L which usually refresh the prompt and harmless to send as keepalive
        self.keepalive_pattern = "\x0C".encode("UTF-8")
        self.conn = connection
        self.transfer_feature_to_clean = []

    @abstractmethod
    async def check_device_file(
        self, device_fs: Optional[str], file_name: str
    ) -> FileCheckResult:
        """
        Check remote file and storage space
        Returning empty hash means error accessing the file

        Args:
            device_fs: filesystem on device (e.g. disk0:/)
            file_name: file to examine

        Returns:
            FileCheckResult
        """
        ...

    @abstractmethod
    async def _ensure_transfer_capability(  # noqa: C901
        self, force: Optional[bool] = False
    ) -> Union[bool, None]:
        """
        Ensure device is capable of using scp.

        Args:
            force: Try reconfigure device if it doesn't support scp. If set to `None`, don't check
                   anything.

        Returns:
            bool: `True` if device supports scp now and we changed configuration.
                  `False` if device does not support scp or we didn't force configuration which was
                          needed.
                  `None` if we are good to proceed or we didn't check at all.
        """
        ...

    @abstractmethod
    async def _cleanup_after_transfer(self) -> None:
        """
        Device specific cleanup procedure if needed. Useful to restore configuration in case
        _ensure_scp_capability reconfigured the device.

        Returns:
            None
        """
        ...

    @abstractmethod
    async def _get_device_fs(self) -> Optional[str]:
        """
        Device specific drive detection.

        Returns:
            Drive as a string. E.g. disk0:/ or flash0:/
            `None`, if drive not detected or detection is not supported
        """
        ...

    @staticmethod
    async def check_local_file(
        device_fs: Optional[str], file_name: str
    ) -> FileCheckResult:
        """
        Check local file and storage space

        Args:
            device_fs: If specified, this path will be checked for free space. Else path will be
                       taken from `file_name`
            file_name: local file to examine. This should be the full path of local file

        Returns:
            FileCheckResult
        """
        try:
            async with aiofiles.open(file_name, "rb") as f:
                file_hash = hashlib.md5(await f.read()).hexdigest()
                logger.debug(f"'{file_name}' hash is '{file_hash}'")
            file_size = os.path.getsize(file_name)
        except FileNotFoundError:
            file_size = 0
            file_hash = ""

        try:
            path = device_fs or os.path.dirname(file_name)
            # check free space of directory of the file or the local dir
            free_space = shutil.disk_usage(path or ".").free
        except FileNotFoundError:
            free_space = 0

        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)

    @abstractmethod
    async def _async_file_transfer(  # noqa: C901
        self,
        operation: Literal["get", "put"],
        src: str,
        dst: str,
    ) -> bool:
        ...

    async def file_transfer(  # noqa: C901
        self,
        operation: Literal["get", "put"],
        src: str,
        dst: str = "",
        verify: bool = True,
        device_fs: Optional[str] = None,
        overwrite: bool = False,
        force_config: bool = False,
        cleanup: bool = True,
    ) -> FileTransferResult:
        """SCP for network devices

        This transfer is idempotent and does the following checks before/after transfer:

        #. | checksum
        #. | existence of file at destination (also with hash)
        #. | available space at destination
        #. | scp enablement on device (and tries to turn it on if needed)
        #. | restore configuration after transfer if it was changed
        #. | check MD5 after transfer

        The file won't be transferred if the hash of the files on local/device are the same!

        Args:
            operation: put/get file to/from device
            src: source file name
            dst: destination file name (same as src if omitted)
            verify: `True` if verification is needed (checksum, file existence, disk space)
            device_fs: IOS device filesystem (autodetect if empty)
            overwrite: If set to `True`, destination will be overwritten in case hash verification
                       fails
                       If set to `False`, destination file won't be overwritten.
                       Beware: turning off `verify` will make this parameter ignored and destination
                        will be overwritten regardless! (Logic is that if user does not care about
                        checking, just copy it over)
            force_config: If set to `True`, Transfer function will be enabled in device configuration
                               before transfer.
                              If set to `False`, Transfer functionality will be checked but won't
                              configure the device.
                              If set to `None`, capability won't even checked.
            cleanup: If set to True, call the cleanup procedure to restore configuration if it was
                     altered

        Returns:
            FileTransferResult
        """

        if operation not in ["get", "put"]:
            raise ValueError(f"Operation '{operation}' is not supported")

        transfer_result = FileTransferResult(False, False, False)
        src_file_data = FileCheckResult("", 0, 0)
        dst_file_data = FileCheckResult("", 0, 0)

        dst_check, src_check = (None, None)
        dst_device_fs: Optional[str] = None
        src_device_fs: Optional[str] = None

        # set destination filename to source if missing
        if dst in {"", "."}:
            # set destination to filename and strip all path
            dst = PurePath(src).name

        if operation == "get":
            src_check = self.check_device_file
            src_device_fs = device_fs or await self._get_device_fs()
            dst_check = self.check_local_file

        if operation == "put":
            src_check = self.check_local_file
            dst_device_fs = device_fs or await self._get_device_fs()
            dst_check = self.check_device_file

        if verify:
            # gather info on source side
            src_file_data = await src_check(src_device_fs, src)
            logger.debug(f"Source file '{src}': {src_file_data}")
            if not src_file_data.hash:
                logger.warning(f"Source file '{src}' does NOT exists!")
                return transfer_result

            # gather info on destination file
            dst_file_data = await dst_check(dst_device_fs, dst)
            logger.debug(f"Destination file '{dst}': {dst_file_data}")
            if dst_file_data.hash:
                transfer_result.exists = True
                if src_file_data.hash == dst_file_data.hash:
                    transfer_result.verified = True
                    logger.debug(
                        f"'{dst}' file already exists at destination and verified OK"
                    )
                    if not overwrite:
                        return transfer_result

            # if hash does not match and we want to overwrite
            if dst_file_data.hash and not overwrite:
                logger.warning(f"'{dst}' file will NOT be overwritten!")
                return transfer_result

            # check if we have enough free space to transfer the file
            if dst_file_data.free < src_file_data.size:
                logger.warning(
                    f"'{dst}' file is too big ({src_file_data.size}). Destination free space: "
                    f"{dst_file_data.free}"
                )
                return transfer_result

        # check if we are capable of transferring files
        transfer_capability = await self._ensure_transfer_capability(force=force_config)
        if transfer_capability is False:
            logger.error("Transfer feature is not enabled on device!")
            return transfer_result

        try:
            logger.info(f"{operation} '{src}' as '{dst}'")
            _transferred = await self._async_file_transfer(
                operation,
                src,
                dst,
            )
            transfer_result.transferred = _transferred
            transfer_result.exists = True
        except Exception as e:
            raise e

        if cleanup and self.transfer_feature_to_clean:
            await self._cleanup_after_transfer()

        if verify:
            await self._verify_transfer(
                dst, dst_check, dst_device_fs, src_file_data, transfer_result
            )

        return transfer_result

    @staticmethod
    async def _verify_transfer(
        dst, dst_check, dst_device_fs, src_file_data, transfer_result
    ):
        # check destination file after copy
        dst_file_data = await dst_check(dst_device_fs, dst)
        # check if file was created
        if dst_file_data.hash:
            transfer_result.exists = True
        # check if file has the same hash as source
        if dst_file_data.hash and dst_file_data.hash == src_file_data.hash:
            transfer_result.verified = True
        else:
            logger.warning(f"'{dst}' failed hash verification!")
