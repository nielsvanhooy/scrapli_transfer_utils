import pytest
from scrapli.driver.core import AsyncIOSXEDriver
from scrapli_community.huawei.vrp.async_driver import AsyncHuaweiVRPDriver

from scrapli_transfer_utils.async_transfer.asyncscp.cisco_iosxe import AsyncSCPIOSXE
from scrapli_transfer_utils.async_transfer.asyncsftp.huawei_vrp import (
    AsyncSFTPHuaweiVrp,
)
from scrapli_transfer_utils.factory import AsyncSrapliTransferUtils


async def test_scp_factory_iosxe(async_scp_iosxe_object):
    scp_cisco_ios_xe = AsyncSrapliTransferUtils(async_scp_iosxe_object)

    assert isinstance(async_scp_iosxe_object, AsyncIOSXEDriver)
    assert isinstance(scp_cisco_ios_xe, AsyncSCPIOSXE)


async def test_sftp_factory_huawei_vrp(async_sftp_huawei_vrp_object):
    sftp_huawei_vrp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)

    assert isinstance(async_sftp_huawei_vrp_object, AsyncHuaweiVRPDriver)
    assert isinstance(sftp_huawei_vrp, AsyncSFTPHuaweiVrp)


# async def test_factory_with_sync_fail(async_sftp_huawei_vrp_object):
#     sftp_huawei_vrp = AsyncSrapliTransferUtils(async_sftp_huawei_vrp_object)
#
#     assert isinstance(async_sftp_huawei_vrp_object, AsyncHuaweiVRPDriver)
#     assert isinstance(sftp_huawei_vrp, AsyncSFTPHuaweiVrp)
