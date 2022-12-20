import asyncio

from scrapli.driver.core import AsyncIOSXEDriver
from scrapli_community.huawei.vrp.huawei_vrp import (
    DEFAULT_PRIVILEGE_LEVELS as VRP_DEFAULT_PRIVILEGE_LEVELS,
)
from scrapli_community.huawei.vrp.async_driver import (
    AsyncHuaweiVRPDriver,
    default_async_on_open,
    default_async_on_close,
)

from scrapli_transfer_utils.factory import AsyncSrapliTransferUtils


async def make_connection_scrapli_sync_iosxe():
    running_config = "running-config"
    startup_config = "startup-config"
    my_device = {
        "host": "10.1.1.142",
        "auth_username": "lagen008",
        "auth_password": "lagen008",
        "auth_strict_key": False,
        "transport": "asyncssh",
        "ssh_config_file": "/home/donnyio/git/scrapli_cfg/config",
    }

    conn = AsyncIOSXEDriver(**my_device)
    async with conn as session:
        await session.open()
        await session.send_command("show run")
        scp = AsyncSrapliTransferUtils(conn)
        result = await scp.file_transfer(
            "get",
            src=running_config,
            dst=".",
            device_fs="system:",
            force_config=True,
            verify=True,
        )
        result_two = await scp.file_transfer(
            "put",
            src=running_config,
            dst="running_config",
            device_fs="flash:",
            force_config=True,
            verify=True,
        )
        lala = "loeloe"


async def make_connection_scrapli_async_huawei_vpr():
    filename = "running-config"
    my_device = {
        "host": "10.1.1.131",
        "auth_username": "lagen008",
        "auth_password": "lagen008",
        "auth_strict_key": False,
        "transport": "asyncssh",
        "privilege_levels": VRP_DEFAULT_PRIVILEGE_LEVELS,
        "default_desired_privilege_level": "privilege_exec",
        "ssh_config_file": "/home/donnyio/git/scrapli_cfg/config",
        "on_open": default_async_on_open,
        "on_close": default_async_on_close,
    }

    conn = AsyncHuaweiVRPDriver(**my_device)
    async with conn as session:
        await session.open()
        await session.send_command("display interfaces")
        sftp = AsyncSrapliTransferUtils(conn)
        result_get = await sftp.file_transfer(
            "get",
            src="21500104832SL5600370-1668688866694.cfg",
            dst="/tmp/lala",
            force_config=True,
            verify=True,
            cleanup=True,
        )
        # result_put = await sftp.file_transfer("put", src="/tmp/lala", dst="lala",
        #                                       device_fs="flash:",
        #                                       force_config=True)
        lala = "loeloe"

    # make_connection_scrapli_sync()


asyncio.run(make_connection_scrapli_sync_iosxe())
# asyncio.run(make_connection_scrapli_async_huawei_vpr())
