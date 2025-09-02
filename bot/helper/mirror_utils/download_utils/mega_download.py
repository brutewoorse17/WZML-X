#!/usr/bin/env python3
from secrets import token_hex
from aiofiles.os import makedirs
from asyncio import Event
from mega import MegaApi, MegaListener, MegaRequest, MegaTransfer, MegaError
from urllib.parse import urlparse
import random

from bot import (
    LOGGER,
    config_dict,
    download_dict_lock,
    download_dict,
    non_queued_dl,
    queue_dict_lock,
    bot_cache,
)
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import (
    get_mega_link_type,
    async_to_sync,
    sync_to_async,
)
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.task_manager import (
    is_queued,
    limit_checker,
    stop_duplicate_check,
)


def _parse_proxy_list_from_config():
    proxies = []
    proxy_single = (config_dict.get("MEGA_PROXY") or "").strip()
    proxy_multi = (config_dict.get("MEGA_PROXIES") or "").strip()
    proxy_file = (config_dict.get("MEGA_PROXY_FILE") or "").strip()

    if proxy_single:
        proxies.append(proxy_single)

    if proxy_multi:
        # split by newline or comma or whitespace
        for part in proxy_multi.replace(",", "\n").splitlines():
            p = part.strip()
            if p and not p.startswith("#"):
                proxies.append(p)

    if proxy_file:
        try:
            with open(proxy_file, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if raw and not raw.startswith("#"):
                        proxies.append(raw)
        except Exception as e:
            LOGGER.error(f"Failed reading MEGA proxy file '{proxy_file}': {e}")

    # de-duplicate preserving order
    seen = set()
    unique = []
    for p in proxies:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def _choose_proxy(proxies):
    strategy = (config_dict.get("MEGA_PROXY_STRATEGY") or "round-robin").strip().lower()
    state = bot_cache.setdefault("mega_proxy_state", {"last_index": -1})
    if not proxies:
        return None
    if strategy == "random":
        idx = random.randrange(len(proxies))
    else:
        last_index = state.get("last_index", -1)
        idx = (last_index + 1) % len(proxies)
        state["last_index"] = idx
    return proxies[idx]


def _apply_proxy(api: MegaApi):
    try:
        proxies = _parse_proxy_list_from_config()
        proxy_url = _choose_proxy(proxies)
        if not proxy_url:
            return
        # Lazy import to avoid hard dependency if MegaProxy is unavailable
        try:
            import mega as mega_mod
            MegaProxy = getattr(mega_mod, "MegaProxy", None)
        except Exception as e:
            MegaProxy = None
            LOGGER.error(f"Failed to import MegaProxy: {e}")

        if MegaProxy is None:
            LOGGER.warning("MegaProxy class not available; skipping proxy apply")
            return

        proxy = MegaProxy()
        # Best effort: prefer setProxyURL if available
        if hasattr(proxy, "setProxyURL"):
            try:
                proxy.setProxyURL(proxy_url)
            except Exception as e:
                LOGGER.error(f"setProxyURL failed: {e}")
        else:
            # Fallback: set type by scheme if possible
            try:
                parsed = urlparse(proxy_url)
                scheme = (parsed.scheme or "").lower()
                if hasattr(MegaProxy, "PROXY_SOCKS5") and scheme.startswith("socks"):
                    proxy.setProxyType(getattr(MegaProxy, "PROXY_SOCKS5"))
                elif hasattr(MegaProxy, "PROXY_HTTP"):
                    proxy.setProxyType(getattr(MegaProxy, "PROXY_HTTP"))
                host = parsed.hostname or ""
                port = parsed.port or 0
                if hasattr(proxy, "setProxyHost"):
                    proxy.setProxyHost(host)
                if hasattr(proxy, "setProxyPort") and port:
                    proxy.setProxyPort(port)
                if parsed.username and hasattr(proxy, "setProxyUsername"):
                    proxy.setProxyUsername(parsed.username)
                if parsed.password and hasattr(proxy, "setProxyPassword"):
                    proxy.setProxyPassword(parsed.password)
            except Exception as e:
                LOGGER.error(f"Fallback proxy setup failed: {e}")

        # Apply to api
        if hasattr(api, "setProxySettings"):
            try:
                api.setProxySettings(proxy)
                LOGGER.info(f"Applied MEGA proxy: {proxy_url}")
            except Exception as e:
                LOGGER.error(f"setProxySettings failed: {e}")
        else:
            LOGGER.warning("MegaApi.setProxySettings not available; proxy not applied")
    except Exception as e:
        LOGGER.error(f"Unexpected error while applying proxy: {e}")


class MegaAppListener(MegaListener):
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)
    NO_ERROR = "no error"

    def __init__(self, continue_event: Event, listener):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self.__bytes_transferred = 0
        self.__speed = 0
        self.__name = ""
        super().__init__()

    @property
    def speed(self):
        return self.__speed

    @property
    def downloaded_bytes(self):
        return self.__bytes_transferred

    def onRequestFinish(self, api, request, error):
        if str(error).lower() != "no error":
            self.error = error.copy()
            LOGGER.error(f"Mega onRequestFinishError: {self.error}")
            self.continue_event.set()
            return
        request_type = request.getType()
        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
            self.__name = self.public_node.getName()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode()
            self.__name = self.node.getName()
            LOGGER.info(f"Node Name: {self.node.getName()}")
        if (
            request_type not in self._NO_EVENT_ON
            or self.node
            and "cloud drive" not in self.__name.lower()
        ):
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f"Mega Request error in {error}")
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(
                self.listener.onDownloadError, f"RequestTempError: {error.toString()}"
            )
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self.__speed = transfer.getSpeed()
        self.__bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (
                transfer.isFolderTransfer() or transfer.getFileName() == self.__name
            ):
                async_to_sync(self.listener.onDownloadComplete)
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        filen = transfer.getFileName()
        state = transfer.getState()
        errStr = error.toString()
        LOGGER.error(f"Mega download error in file {transfer} {filen}: {error}")
        if state in [1, 4]:
            # Sometimes MEGA (offical client) can't stream a node either and raises a temp failed error.
            # Don't break the transfer queue if transfer's in queued (1) or retrying (4) state [causes seg fault]
            return

        self.error = errStr
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(
                self.listener.onDownloadError, f"TransferTempError: {errStr} ({filen})"
            )
            self.continue_event.set()

    async def cancel_download(self):
        self.is_cancelled = True
        await self.listener.onDownloadError("Download Canceled by user")


class AsyncExecutor:

    def __init__(self):
        self.continue_event = Event()

    async def do(self, function, args):
        self.continue_event.clear()
        await sync_to_async(function, *args)
        await self.continue_event.wait()


async def add_mega_download(mega_link, path, listener, name):
    MEGA_EMAIL = config_dict["MEGA_EMAIL"]
    MEGA_PASSWORD = config_dict["MEGA_PASSWORD"]

    executor = AsyncExecutor()
    api = MegaApi(None, None, None, "WZML-X")
    folder_api = None

    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)

    # Apply rotating proxy if configured
    _apply_proxy(api)

    if MEGA_EMAIL and MEGA_PASSWORD:
        await executor.do(api.login, (MEGA_EMAIL, MEGA_PASSWORD))

    if get_mega_link_type(mega_link) == "file":
        await executor.do(api.getPublicNode, (mega_link,))
        node = mega_listener.public_node
    else:
        folder_api = MegaApi(None, None, None, "WZML-X")
        folder_api.addListener(mega_listener)
        # Apply rotating proxy to folder_api too
        _apply_proxy(folder_api)
        await executor.do(folder_api.loginToFolder, (mega_link,))
        node = await sync_to_async(folder_api.authorizeNode, mega_listener.node)
    if mega_listener.error is not None:
        await sendMessage(listener.message, str(mega_listener.error))
        await executor.do(api.logout, ())
        if folder_api is not None:
            await executor.do(folder_api.logout, ())
        return

    name = name or node.getName()
    msg, button = await stop_duplicate_check(name, listener)
    if msg:
        await sendMessage(listener.message, msg, button)
        await executor.do(api.logout, ())
        if folder_api is not None:
            await executor.do(folder_api.logout, ())
        return

    gid = token_hex(5)
    size = api.getSize(node)
    if limit_exceeded := await limit_checker(size, listener, isMega=True):
        await sendMessage(listener.message, limit_exceeded)
        return
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(name, size, gid, listener, "Dl")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                await executor.do(api.logout, ())
                if folder_api is not None:
                    await executor.do(folder_api.logout, ())
                return
        from_queue = True
        LOGGER.info(f"Start Queued Download from Mega: {name}")
    else:
        from_queue = False

    async with download_dict_lock:
        download_dict[listener.uid] = MegaDownloadStatus(
            name, size, gid, mega_listener, listener.message, listener.upload_details
        )
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f"Start Queued Download from Mega: {name}")
    else:
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        LOGGER.info(f"Download from Mega: {name}")

    await makedirs(path, exist_ok=True)
    await executor.do(api.startDownload, (node, path, name, None, False, None))
    await executor.do(api.logout, ())
    if folder_api is not None:
        await executor.do(folder_api.logout, ())
