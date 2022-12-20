from unittest import mock

import pytest

from scrapli_transfer_utils.async_transfer.asyncscp.cisco_iosxe import AsyncSCPIOSXE
from scrapli_transfer_utils.async_transfer.asyncsftp.huawei_vrp import (
    AsyncSFTPHuaweiVrp,
)
from scrapli_transfer_utils.async_transfer.base import AsyncTransferFeature
from scrapli_transfer_utils.dataclasses import FileTransferResult
from scrapli_transfer_utils.factory import AsyncSrapliTransferUtils


@pytest.mark.scrapli_replay
async def test_check_local_file_succes(async_scp_iosxe_object):
    file_name = "files/test_file.txt"

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        check_file = await scp.check_local_file(device_fs="", file_name=file_name)

        assert check_file.hash == "2cc937eb4a09d18565fde23002a35284"
        assert check_file.size == 31


@pytest.mark.scrapli_replay
async def test_check_local_file_fail(async_scp_iosxe_object):
    file_name = "i_dont_exist.txt"

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        check_file = await scp.check_local_file(device_fs="", file_name=file_name)

        assert check_file.hash == ""
        assert check_file.size == 0


@pytest.mark.scrapli_replay
async def test_file_transfer_all_opts(async_scp_iosxe_object):

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        with mock.patch.object(
            AsyncSCPIOSXE, "_async_file_transfer"
        ) as _async_file_transfer:
            _async_file_transfer.return_value = True
            file_trans = await scp.file_transfer(
                operation="get",
                src="running_config",
                dst="files/test.txt",
                verify=True,
                device_fs="",
                overwrite=True,
                force_config=True,
                cleanup=True,
            )
            assert file_trans.transferred is True
            assert file_trans.exists is False
            assert file_trans.verified is True


@pytest.mark.scrapli_replay
async def test_file_transfer_all_overwrite_false(async_scp_iosxe_object):

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        with mock.patch.object(AsyncTransferFeature, "check_local_file") as dst_check:
            dst_check.return_value.hash = "0d016eab174e8f56af79d9a99167fc23"

            file_trans = await scp.file_transfer(
                operation="get",
                src="running_config",
                verify=True,
                overwrite=False,
                force_config=True,
                cleanup=True,
            )
            assert file_trans.transferred is False
            assert file_trans.exists is True
            assert file_trans.verified is True
