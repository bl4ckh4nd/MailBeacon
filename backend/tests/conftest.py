import pytest
import aiohttp
from app.config import Settings
from backend.app.core.beacon import MailBeacon
from app.core.dns_utils import create_resolver, DnsResolver
from typing import AsyncGenerator

@pytest.fixture
async def http_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.fixture
def settings() -> Settings:
    return Settings(
        debug=True,
        smtp_timeout=2,
        smtp_verify_timeout=1,
        scraping_timeout=5
    )

@pytest.fixture
async def dns_resolver(settings: Settings) -> DnsResolver:
    return await create_resolver(settings)

@pytest.fixture
async def mail_beacon(http_session: aiohttp.ClientSession, dns_resolver: DnsResolver, settings: Settings) -> MailBeacon:
    return MailBeacon(
        settings=settings,
        http_session=http_session,
        dns_resolver=dns_resolver
    )
