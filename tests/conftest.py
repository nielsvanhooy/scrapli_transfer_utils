import pytest
from scrapli.driver.core import AsyncIOSXEDriver
from scrapli_community.huawei.vrp.huawei_vrp import (
    DEFAULT_PRIVILEGE_LEVELS as VRP_DEFAULT_PRIVILEGE_LEVELS,
)
from scrapli_community.huawei.vrp.async_driver import (
    default_async_on_open,
    default_async_on_close,
    AsyncHuaweiVRPDriver,
)

MY_DEVICE_IOSXE = {
    "host": "10.1.1.154",
    "auth_username": "test008",
    "auth_password": "test008",
    "auth_strict_key": False,
    "ssh_config_file": "config",
    "transport": "asyncssh",
    "auth_private_key": "",
}

MY_DEVICE_HUAWEI_VRP = {
    "host": "10.1.1.131",
    "auth_username": "test008",
    "auth_password": "test008",
    "auth_strict_key": False,
    "ssh_config_file": "config",
    "transport": "asyncssh",
    "privilege_levels": VRP_DEFAULT_PRIVILEGE_LEVELS,
    "default_desired_privilege_level": "privilege_exec",
    "auth_private_key": "",
    "on_open": default_async_on_open,
    "on_close": default_async_on_close,
}


@pytest.fixture(scope="function")
def async_scp_iosxe_object():
    return AsyncIOSXEDriver(**MY_DEVICE_IOSXE)


@pytest.fixture(scope="function")
def async_sftp_huawei_vrp_object():
    return AsyncHuaweiVRPDriver(**MY_DEVICE_HUAWEI_VRP)
