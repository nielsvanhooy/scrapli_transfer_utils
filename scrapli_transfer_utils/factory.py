"""scrapli_scp.factory"""
from scrapli.driver.network import AsyncNetworkDriver, NetworkDriver
from scrapli.driver.core import (
    AsyncIOSXEDriver,
)
from scrapli_community.huawei.vrp.async_driver import AsyncHuaweiVRPDriver

from scrapli_transfer_utils.async_transfer.asyncscp.cisco_iosxe import AsyncSCPIOSXE
from scrapli_transfer_utils.async_transfer.asyncsftp.huawei_vrp import (
    AsyncSFTPHuaweiVrp,
)
from scrapli_transfer_utils.async_transfer.base import AsyncTransferFeature
from scrapli_transfer_utils.exceptions import ScrapliSCPException

ASYNC_CORE_PLATFORM_MAP = {
    AsyncIOSXEDriver: AsyncSCPIOSXE,
    AsyncHuaweiVRPDriver: AsyncSFTPHuaweiVrp,
}


def AsyncSrapliTransferUtils(conn: AsyncNetworkDriver) -> "AsyncTransferFeature":
    if isinstance(conn, NetworkDriver):
        raise ScrapliSCPException(
            "provided scrapli connection is sync but using 'AsyncScrapliCfg' -- you must use an "
            "async connection with 'AsyncScrapliCfg'!"
        )
    platform_class = ASYNC_CORE_PLATFORM_MAP.get(type(conn))
    if not platform_class:
        raise ScrapliSCPException(
            f"scrapli connection object type '{type(conn)}' not a supported scrapli-scp type"
        )
    final_platform: "AsyncTransferFeature" = platform_class(conn)

    return final_platform
