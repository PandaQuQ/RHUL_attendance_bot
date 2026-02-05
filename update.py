import os
import sys
import time
import threading
import subprocess
import logging


def _prompt_update_with_timeout(timeout=10):
    user_input = {"val": None}

    def _reader():
        try:
            user_input["val"] = input().strip().lower()
        except Exception:
            user_input["val"] = None

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    for remaining in range(timeout, 0, -1):
        if user_input["val"] is not None:
            break
        print(
            f"\rA new update is available. Update now? (y/n) Auto-skip in {remaining}s: ",
            end="",
            flush=True,
        )
        time.sleep(1)
    print()
    return user_input["val"]


def check_for_updates(logger=None, timeout=10):
    try:
        local_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        remote_commit = subprocess.check_output(["git", "ls-remote", "origin", "HEAD"]).decode().split()[0]
        if local_commit != remote_commit:
            if logger:
                logger.info("New update detected.")
            user_input = _prompt_update_with_timeout(timeout=timeout)
            if user_input in ("", "y", "yes"):
                if logger:
                    logger.info("Updating the script...")
                subprocess.check_call(["git", "pull"])
                if logger:
                    logger.info("Update successful. Restarting the script...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                if logger:
                    logger.info("Skipping update. Continuing with the current version.")
        else:
            if logger:
                logger.info("No updates found. Continuing execution.", extra={"gray": True})
    except Exception as e:
        if logger:
            logger.error(f"Failed to check for updates: {e}", exc_info=True)
        else:
            raise
