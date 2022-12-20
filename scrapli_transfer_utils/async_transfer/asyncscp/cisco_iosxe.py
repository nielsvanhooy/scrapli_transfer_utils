"""scrapli_scp.asyncssh.cisco"""
import asyncio
import re
from time import time
from typing import Any, List, Optional, Union, Literal, Callable

import asyncssh
from asyncssh import connect, scp

from scrapli_transfer_utils.async_transfer.base import AsyncTransferFeature
from scrapli_transfer_utils.dataclasses import (
    FileCheckResult,
    SCPConnectionParameterType,
)
from scrapli_transfer_utils.logging import logger


class AsyncSCPIOSXE(AsyncTransferFeature):
    def __init__(self, *args: Any, **kwargs: Any):
        self._scp_to_clean: List[str] = []
        super().__init__(*args, **kwargs)

    async def check_device_file(
        self, device_fs: Optional[str], file_name: str
    ) -> FileCheckResult:
        logger.debug(f"Checking {device_fs}{file_name} MD5 hash..")
        outputs = await self.conn.send_commands(
            [
                f"verify /md5 {device_fs}{file_name}",
                f"dir {device_fs}{file_name}",
                rf"dir {device_fs} | i free\)$",
            ],
            timeout_ops=300,
        )
        m = re.search(r"^verify.*=\s*(?P<hash>\w{32})", outputs[0].result, re.M)
        if m:
            file_hash = m.group("hash")
            logger.debug(f"'{file_name}' hash is '{file_hash}'")
        else:
            file_hash = ""
        m = re.search(
            r"^\s*\d+\s*[rw-]+\s*(?P<size>\d+).*" + file_name, outputs[1].result, re.M
        )
        if m:
            file_size = int(m.group("size"))
        else:
            file_size = 0
        m = re.search(r"\((?P<free>\d+) bytes free\)", outputs[2].result, re.M)
        if m:
            free_space = int(m.group("free"))
        else:
            free_space = 0
        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)

    async def _ensure_transfer_capability(  # noqa: C901
        self, force: Optional[bool] = False
    ) -> Union[bool, None]:

        output = await self.conn.send_command(
            "sh run all | i ^ip scp server enable|^ip tcp window|^ip ssh window"
        )
        outputs = output.result.split("\n")
        # find missing or to be adjusted commands
        scp_to_apply = []
        self.transfer_feature_to_clean = []
        # check if SCP is enabled
        if "ip scp server enable" not in outputs:
            scp_to_apply.append("ip scp server enable")
            self.transfer_feature_to_clean.append("no ip scp server enable")
        # check SSH window size. It might not be supported (old IOS)
        try:
            ssh_window_str = [x for x in outputs if "ip ssh" in x][0]
        except IndexError:
            ssh_window_str = ""
        if ssh_window_str:
            m = re.search(r"ip ssh window-size (?P<ssh_window>\d+)", ssh_window_str)
            ssh_window = int(m["ssh_window"] if m else 9999999)
            # intended configuration:
            #
            # ip scp server enable
            # ip ssh window-size 65536
            # ip tcp window-size 65536
            #
            # ip ssh window-size is supported from 16.6.1
            # 65536 is a recommendation by Cisco
            # https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/sec_usr_ssh/configuration/xe-16-6/sec-usr-ssh-xe-16-6-book/sec-usr-ssh-xe-16-book_chapter_0110.html
            window_size = 65536
            if ssh_window < window_size:
                scp_to_apply.append(f"ip ssh window-size {window_size}")
                self.transfer_feature_to_clean.append(
                    f"ip ssh window-size {ssh_window}"
                )
            # TCP window is only interesting if SCP window is supported
            try:
                tcp_window_str = [x for x in outputs if "ip tcp" in x][0]
            except IndexError:
                tcp_window_str = ""
            if tcp_window_str:
                m = re.search(r"ip tcp window-size (?P<tcp_window>\d+)", tcp_window_str)
                tcp_window = int(m["tcp_window"] if m else 9999999)
                if tcp_window < window_size:
                    scp_to_apply.append(f"ip tcp window-size {window_size}")
                    self.transfer_feature_to_clean.append(
                        f"ip tcp window-size {tcp_window}"
                    )

        # check if we are good
        if not scp_to_apply:
            return True

        if not force:
            if "ip scp server enable" in scp_to_apply:
                self.transfer_feature_to_clean = []
                return False
            return False
        # apply SCP enablement
        output_apply = await self.conn.send_configs(scp_to_apply)

        if output_apply.failed:
            # commands did not succeed
            # try to revert
            await self.conn.send_configs(self.transfer_feature_to_clean)
            self.transfer_feature_to_clean = []
            return False
        else:
            # device reconfigured for scp
            return True

    async def _cleanup_after_transfer(self) -> None:
        # we assume that _scp_to_clean was populated by a previously called _ensure_scp_capability
        if not self._scp_to_clean:
            return
        await self.conn.send_configs(self._scp_to_clean)

    async def _get_device_fs(self) -> Optional[str]:
        #  Enable mode needed
        await self.conn.acquire_priv(self.conn.default_desired_privilege_level)
        output = await self.conn.send_command("dir | i Directory of (.*)")
        m = re.match("Directory of (?P<fs>.*)", output.result, re.M)
        if m:
            return m.group("fs")

        return None

    async def _async_file_transfer(  # noqa: C901
        self,
        operation: Literal["get", "put"],
        src: str,
        dst: str,
        progress_handler: Optional[Callable] = None,
        prevent_timeout: Optional[float] = None,
    ) -> bool:
        """
        SCP a file from device to localhost

        Args:
            operation: 'get' or 'put' files from or to the device
            src: Source file name
            dst: Destination file name
            progress_handler: scp callback function to be able to follow the copy progress
            prevent_timeout: interval in seconds when we send an empty command to keep SSH channel
                             up, 0 to turn it off,
                             default is same as `timeout_ops`

        Returns:
            bool: True on success
        """
        result = False

        start_time = 0.0
        if prevent_timeout is None:
            prevent_timeout = self.conn.timeout_ops

        async def _prevent_timeout():
            """Send enter to idle SSH channel to prevent timing out while transferring file"""
            logger.debug("Sending keepalive to device")
            self.conn.transport.write(self.keepalive_pattern)

        def timed_progress_handler(srcpath, dstpath, copied, total):
            """Progress handler wrapper which prevents timeouts while file transfer"""
            nonlocal start_time

            now = time()
            if 0 < prevent_timeout <= (now - start_time):
                logger.debug("Preventing timeout")
                asyncio.ensure_future(_prevent_timeout())
                start_time = now

            # call original handler if specified
            if progress_handler:
                progress_handler(srcpath, dstpath, copied, total)

        # noinspection PyProtectedMember
        scp_options = SCPConnectionParameterType(
            username=self.conn.auth_username,
            password=self.conn.auth_password,
            port=self.conn.port,
            host=self.conn.host,
            options=self.conn.transport.session._options,  # noqa: W0212
        )
        result = False
        try:
            async with connect(**scp_options) as scp_conn:
                start_time = time()
                if operation == "get":
                    await scp(
                        (scp_conn, src),
                        dst,
                        progress_handler=timed_progress_handler,
                        block_size=65536,
                    )
                elif operation == "put":
                    await scp(
                        src,
                        (scp_conn, dst),
                        progress_handler=timed_progress_handler,
                        block_size=65536,
                    )
                else:
                    raise ValueError(f"Invalid operation: {operation}")
        except asyncssh.SFTPError as e:
            result = False
            logger.warning(f"SCP error: {e}")
        except Exception as e:
            result = False
            logger.warning(f"Other error: {e}")
            raise e
        else:
            result = True

        return result
