import asyncio
from asyncio.subprocess import Process
from unittest import mock
from unittest.mock import patch

import pytest
from scrapli_community.huawei.vrp.async_driver import AsyncHuaweiVRPDriver

from scrapli_transfer_utils.async_transfer.asyncsftp.huawei_vrp import (
    AsyncSFTPHuaweiVrp,
)
from scrapli_transfer_utils.factory import AsyncSrapliTransferUtils


@pytest.mark.scrapli_replay
async def test_check_device_file_huawei_vrp_succes(async_sftp_huawei_vrp_object):
    device_fs = "flash:/"
    file_name = "axess_20250205132038.cfg"

    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        check_file = await sftp.check_device_file(device_fs, file_name)

        assert check_file.hash == "259bb20835c70bce41765234d9b812de"
        assert check_file.free == 379748000
        assert check_file.size == 14917000


@pytest.mark.scrapli_replay
async def test_check_device_file_huawei_vrp_fail(async_sftp_huawei_vrp_object):
    device_fs = "flash:/"
    file_name = "file_not_here"

    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        check_file = await sftp.check_device_file(device_fs, file_name)

        assert check_file.hash == ""
        assert check_file.free == 379748000
        assert check_file.size == 0


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_vrp_force_false_but_config(
    async_sftp_huawei_vrp_object,
):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)
        value = await sftp._ensure_transfer_capability(force=False)

        assert value is True


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_vrp_force_false_but_no_config(
    async_sftp_huawei_vrp_object,
):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        with mock.patch.object(
            AsyncHuaweiVRPDriver, "send_command", autospec=True
        ) as send_command:
            send_command.return_value.result = ""
            value = await sftp._ensure_transfer_capability(force=False)

            assert sftp.transfer_feature_to_clean == []
            assert value is False


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_vrp_force(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        with mock.patch.object(
            AsyncHuaweiVRPDriver, "send_command", autospec=True
        ) as send_command:
            send_command.return_value.result = ""
            value = await sftp._ensure_transfer_capability(force=True)

            assert value is True


@pytest.mark.scrapli_replay
async def test_cleanup_after_transfer_vrp_true(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        with mock.patch.object(
            AsyncHuaweiVRPDriver, "send_configs", autospec=True
        ) as send_configs:
            sftp.transfer_feature_to_clean = ["undo sftp server enable"]
            value = await sftp._cleanup_after_transfer()
            assert value is True


@pytest.mark.scrapli_replay
async def test_cleanup_after_transfer_vrp_false(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        value = await sftp._cleanup_after_transfer()
        assert value is False


@pytest.mark.scrapli_replay
async def test_get_device_fs_vrp(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        value = await sftp._get_device_fs()
        assert value == "flash:/"


@pytest.mark.scrapli_replay
async def test_async_file_transfer_vrp_fail(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        with mock.patch.object(Process, "communicate", autospec=True) as communicate:
            communicate.return_value = (b"lala", b"No such file or directory")
            with pytest.raises(FileNotFoundError) as exc_info:
                await sftp._async_file_transfer("get", "config", ".")


@pytest.mark.scrapli_replay
async def test_async_file_transfer_vrp_succes(async_sftp_huawei_vrp_object):
    async with async_sftp_huawei_vrp_object as session:
        await session.open()
        sftp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

        with mock.patch.object(Process, "communicate", autospec=True) as communicate:
            communicate.return_value = (b"lala", b"loeloe")
            file_trans = await sftp._async_file_transfer("get", "config", ".")
            assert file_trans == True
