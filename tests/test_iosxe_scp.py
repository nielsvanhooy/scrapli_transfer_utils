from unittest import mock

import asyncssh
import pytest
from scrapli.driver.core import AsyncIOSXEDriver

from scrapli_transfer_utils.async_transfer.asyncscp.cisco_iosxe import AsyncSCPIOSXE
from scrapli_transfer_utils.factory import AsyncSrapliTransferUtils


@pytest.mark.scrapli_replay
async def test_check_device_file_iosxe_succes(async_scp_iosxe_object):
    device_fs = "flash:/"
    file_name = "VA_A_39d_B_38h3_24h.bin"

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        check_file = await scp.check_device_file(device_fs, file_name)

        assert check_file.hash == "c61b399f34b178264d23617becf6c88b"
        assert check_file.free == 61063168
        assert check_file.size == 2814938


@pytest.mark.scrapli_replay
async def test_check_device_file_iosxe_fail(async_scp_iosxe_object):
    device_fs = "flash:/"
    file_name = "file_not_here"

    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        check_file = await scp.check_device_file(device_fs, file_name)

        assert check_file.hash == ""
        assert check_file.free == 61063168
        assert check_file.size == 0


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_iosxe_force(async_scp_iosxe_object):
    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        with mock.patch.object(
            AsyncIOSXEDriver, "send_command", autospec=True
        ) as send_command:
            send_command.return_value.result = ""

            value = await scp._ensure_transfer_capability(force=True)

            assert value is True
            assert "no ip scp server enable" in scp.transfer_feature_to_clean


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_iosxe_true_window_size(
    async_scp_iosxe_object,
):
    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        with mock.patch.object(
            AsyncIOSXEDriver, "send_command", autospec=True
        ) as send_command:
            send_command.return_value.result = (
                "ip tcp window-size 656\nip ssh window-size 636\nip scp server enable"
            )

            value = await scp._ensure_transfer_capability(force=True)
            assertion_items = ["ip ssh window-size 636", "ip tcp window-size 656"]
            assert value is True
            assert assertion_items == scp.transfer_feature_to_clean


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_iosxe_force_false_but_config(
    async_scp_iosxe_object,
):
    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)
        value = await scp._ensure_transfer_capability(force=False)

        assert value is True


@pytest.mark.scrapli_replay
async def test_ensure_transfer_capability_iosxe_force_false_but_no_config(
    async_scp_iosxe_object,
):
    async with async_scp_iosxe_object as session:
        await session.open()
        scp = AsyncSrapliTransferUtils(async_scp_iosxe_object)

        with mock.patch.object(
            AsyncIOSXEDriver, "send_command", autospec=True
        ) as send_command:
            send_command.return_value.result = ""

            value = await scp._ensure_transfer_capability(force=False)

            assert scp.transfer_feature_to_clean == []
            assert value is False
