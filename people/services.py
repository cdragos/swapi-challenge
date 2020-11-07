from dateutil.parser import parse
from math import ceil
from pathlib import PosixPath
from typing import Awaitable, Dict, Iterator, Set, List
import asyncio

from asgiref.sync import async_to_sync
from django.conf import settings
from petl.io.json import DictsView
import httpx
import petl as etl


CUTOUT_FIELDS = (
    'films', 'species', 'vehicles', 'starships', 'url', 'created', 'edited')

_API_PER_PAGE = 10


@async_to_sync
async def fetch_data(filename: str) -> PosixPath:
    filepath: PosixPath = settings.DATA_PATH / filename
    url: str = f'{settings.API_BASE_URL}/people/'
    planets: Dict[str, str] = {}

    async with httpx.AsyncClient(timeout=60) as client:
        # call the first page to get the count and the first result set
        # based on count and items per page  we are generating a list of
        # endpoints to call concurrently
        people_r: Awaitable = await client.get(url)
        people_r_data: dict = people_r.json()
        pages: int = ceil(people_r_data['count'] / _API_PER_PAGE)

        people_futures: List[Awaitable] = []
        for page in range(2, pages + 1):
            url: str = f'{settings.API_BASE_URL}/people/?page={page}'
            people_futures.append(client.get(url))

        people_responses: List[httpx.Response] = await asyncio.gather(
            *people_futures)
        people_data: List[dict] = (
            [people_r_data] + [r.json() for r in people_responses])

        # generate a list of endpoints for characters homeworlds
        # and call them concurrently
        planet_futures: List[Awaitable] = []
        for data in people_data:
            homeworlds: Set[str] = {
                p['homeworld'] for p in data['results']
                if p['homeworld'] not in planets
            }
            planet_futures.extend([client.get(h) for h in homeworlds])

        planet_responses: List[httpx.Response] = await asyncio.gather(
            *planet_futures)
        planet_data: Iterator[dict] = (r.json() for r in planet_responses)
        planets.update({p['url']: p['name'] for p in planet_data})

        write_data(filepath, people_data, planets)


def write_data(
    filepath: PosixPath,
    people_data: dict,
    planets: Dict[str, str]
):
    settings.DATA_PATH.mkdir(parents=True, exist_ok=True)
    for data in people_data:
        table: DictsView = etl.fromdicts(
            data['results']
        ).convert(
            'homeworld', planets
        ).addfield(
            'date', lambda row: parse(row['edited']).strftime('​%Y-%m-%d')
        ).cutout(
            *CUTOUT_FIELDS
        )
        if filepath.is_file():
            table.appendcsv(filepath)
        else:
            table.tocsv(filepath)
