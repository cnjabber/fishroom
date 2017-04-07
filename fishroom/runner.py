#!/usr/bin/env python3
import os
import threading
import traceback

from typing import Callable, Tuple, Iterable, Any

from .helpers import get_logger

logger = get_logger(__name__)

AnyFunc = Callable[[Any], Any]
AnyArgs = Tuple[Any]


def run_threads(thread_target_args: Iterable[Tuple[AnyFunc, AnyArgs]]):
    from .telegram import Telegram
    from .config import config

    tasks = []
    DEAD = threading.Event()

    # wrapper to send report traceback info to telegram
    def die(f: AnyFunc):
        logger = get_logger(__name__)

        if "telegram" not in config:
            logger.info("No telegram configured.")
        else:
            tg = Telegram(config["telegram"]["token"])

        def send_all(text):
            for adm in config["telegram"]["admin"]:
                try:
                    tg.send_msg(adm, text, escape=False)
                except:
                    pass

        def wrapper(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except:
                logger.exception("thread failed")
                exc = traceback.format_exc()
                send_all("<code>{}</code>".format(exc))
                DEAD.set()

        return wrapper

    for target, args in thread_target_args:
        t = threading.Thread(target=die(target), args=args)
        t.setDaemon(True)
        t.start()
        tasks.append(t)

    DEAD.wait()
    logger.error("Everybody died, I don't wanna live any more! T_T")
    os._exit(1)


__all__ = [run_threads, ]

# vim: ts=4 sw=4 sts=4 expandtab
