===========
Scrapli SCP
===========
Welcome to Scrapli SCP project!

This project is about to add smart SCP capability to Scrapli based connections.
By smart, I mean various checks before and after the file copy to ensure the file copy is possible
and successful.

These are the checks done by default:

#. checksum
#. existence of file at destination (also with hash)
#. available space at destination
#. scp enablement on device (and tries to turn it on if needed)
#. restore configuration after transfer if it was changed
#. check MD5 after transfer

Requirements
------------
``scrapli``, ``scrapli-community``, ``asyncssh``, ``aiofiles``

and the linux package sftp
``sftp``

Installation
------------
.. code-block:: console

    $ install 'scrapli_transfer_utils @ git+https://github.com/nielsvanhooy/scrapli_transfer_utils.git'


Simple example
--------------
You can find it in ``tests`` folder but the main part:

.. code-block:: python

    async with AsyncScrapli(**device) as conn:
        scp = AsyncSrapliSCP(conn)
        result = await scp.file_transfer("put", src=filename, dst=".", force_scp_config=True)
    print(result)