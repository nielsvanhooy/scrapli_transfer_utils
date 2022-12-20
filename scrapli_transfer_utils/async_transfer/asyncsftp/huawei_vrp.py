import asyncio
import re

from typing import Any, List, Optional, Union, Literal

from scrapli_transfer_utils.async_transfer.base import AsyncTransferFeature
from scrapli_transfer_utils.dataclasses import FileCheckResult
from scrapli_transfer_utils.logging import logger


class AsyncSFTPHuaweiVrp(AsyncTransferFeature):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    async def check_device_file(
        self, device_fs: Optional[str], file_name: str
    ) -> FileCheckResult:
        logger.debug(f"Checking {device_fs}{file_name} MD5 hash..")

        md5_sum_regex = re.compile(r"MD5:\n(?P<md5_sum>.*)", re.M)
        # double {{ }} to escape f string.
        byte_size_regex = re.compile(
            rf"^\s+\d+\s+[\-\w]{{0,5}}\s+(?P<byte_size>.[\d,]+?(?=\s)).+?(?={file_name})",
            re.M,
        )
        free_space_regex = re.compile(
            r"total available\s.(?P<free_space>.+?(?=\s+))", re.M
        )

        outputs = await self.conn.send_commands(
            [
                f"display system file-md5 {device_fs}{file_name}",
                f"dir /all",
            ]
        )
        file_hash = ""
        find_md5_sum = re.search(md5_sum_regex, outputs[0].result)
        if find_md5_sum:
            file_hash = find_md5_sum.group("md5_sum")
            logger.debug(f"'{file_name}' hash is '{file_hash}'")

        file_size = 0
        find_file_size = re.search(byte_size_regex, outputs.data[1].result)
        if find_file_size:
            file_size_kb = find_file_size.group("byte_size").replace(",", "")
            file_size = int(file_size_kb) * 1000

        free_space = 0
        find_free_space = re.search(free_space_regex, outputs.data[1].result)
        if find_free_space:
            free_space_kb = find_free_space.group("free_space").replace(",", "")
            free_space = int(free_space_kb) * 1000

        return FileCheckResult(hash=file_hash, size=file_size, free=free_space)

    async def _ensure_transfer_capability(  # noqa: C901
        self, force: Optional[bool] = False
    ) -> Union[bool, None]:
        # intended configuration:
        #
        # sftp server enable
        # note: this can be different in the future.
        # seeing as i only have devices inside a VPN and tacacs user control.
        # therefore i don't need to create useraccounts. open a PR if you need this.

        output = await self.conn.send_command(
            "display current-configuration | include ^ sftp server enable"
        )

        if "sftp server enable" in output.result:
            self.transfer_feature_to_clean = ["undo sftp server enable"]

        if not force:
            if "sftp server enable" in output.result:
                self.transfer_feature_to_clean = []
                return True
            return False

        # apply SFTP enablement
        output_apply = await self.conn.send_config("sftp server enable")

        if output_apply.failed:
            await self.conn.send_configs(self.transfer_feature_to_clean)
            self.transfer_feature_to_clean = []
            return False
        return True

    async def _cleanup_after_transfer(self) -> bool:
        # we assume that _sftp_to_clean was populated by a previously called _ensure_scp_capability
        if not self.transfer_feature_to_clean:
            return False
        await self.conn.send_configs(self.transfer_feature_to_clean)
        return True

    async def _get_device_fs(self) -> Optional[str]:
        #  Enable mode needed
        output = await self.conn.send_command("dir /all")
        m = re.match("Directory of (?P<fs>.*)", output.result, re.M)
        if m:
            return m.group("fs")

        return None

    async def _async_file_transfer(  # noqa: C901
        self,
        operation: Literal["get", "put"],
        src: str,
        dst: str,
    ) -> bool:

        result = False

        try:
            cmd = (
                f'sshpass -p "{self.conn.auth_password}" sftp {self.conn.auth_username}@{self.conn.host} <<EOF \n'
                f"    {operation} {src} {dst} \n"
                f"EOF"
            )

            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if (
                "No such file or directory" in stderr.decode()
                or "not found" in stderr.decode()
            ):
                raise FileNotFoundError(
                    f"file {src} was not found in {operation} operation"
                )

        except Exception as e:
            logger.warning(f"Other error: {e}")
            raise e
        else:
            result = True

        return result
