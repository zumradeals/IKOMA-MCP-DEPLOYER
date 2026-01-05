from __future__ import annotations

import time
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.deploy.deploy_up import DEFAULT_EXPECTED_STATUS, DEFAULT_HEALTH_INTERVAL, DEFAULT_HEALTH_TIMEOUT, DeployError


def wait_for_health(health: Dict[str, object], logger) -> None:
    url = str(health.get("url"))
    expected_status = int(health.get("expected_status", DEFAULT_EXPECTED_STATUS))
    timeout = int(health.get("timeout", DEFAULT_HEALTH_TIMEOUT))
    interval = int(health.get("interval", DEFAULT_HEALTH_INTERVAL))
    retries = health.get("retries")
    max_attempts = int(retries) if retries is not None else None

    logger.info(
        "Healthcheck HTTP sur %s (attendu=%s, timeout=%ss, interval=%ss, retries=%s)",
        url,
        expected_status,
        timeout,
        interval,
        max_attempts or "illimité",
    )

    deadline = time.time() + timeout
    last_error: str | None = None
    attempts = 0

    while time.time() < deadline:
        if max_attempts is not None and attempts >= max_attempts:
            break
        attempts += 1

        remaining = max(1, int(deadline - time.time()))
        request_timeout = min(interval, remaining)

        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=request_timeout) as resp:  # nosec - URL contrôlée via manifest
                if resp.status == expected_status:
                    logger.info("Healthcheck OK (%s) après %s tentative(s)", resp.status, attempts)
                    return
                last_error = f"Statut inattendu: {resp.status}"
                logger.warning(last_error)
        except (HTTPError, URLError) as exc:
            last_error = f"Erreur HTTP: {exc}"
            logger.warning(last_error)
        except Exception as exc:  # noqa: BLE001
            last_error = f"Erreur non prévue: {exc}"
            logger.warning(last_error)

        time.sleep(interval)

    reason = last_error or f"Healthcheck expiré après {attempts} tentative(s)"
    raise DeployError(reason)
