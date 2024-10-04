# Quick and simple scraper to pull some data from OPGG using multisearch

# Author  : ShoobyDoo
# Date    : 2024-07-10
# License : BSD-3-Clause

from datetime import datetime
import json
from json import JSONDecodeError

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from opgg.cacher import Cacher
from opgg.champion import Champion, Passive, Price, Skin, Spell
from opgg.params import By, Region
from opgg.season import SeasonInfo

"""
### utils.py
A collection of static utility helper methods that perform various opgg and league specific tasks such as fetching champions, seasons, etc.\n

Copyright (c) 2023-2024, ShoobyDoo
License: BSD-3-Clause, See LICENSE for more details.
"""

BASE_API_URL = "https://lol-web-api.op.gg/api/v1.0/internal/bypass"
API_URL = f"{BASE_API_URL}/summoners/{{region}}/{{summoner_id}}/renewal"

ua = UserAgent()
HEADERS = {"User-Agent": ua.random}


def update(summoner_id: str, region: Region = Region.NA) -> dict:
    """
    Send an update request to fetch the latest details for a given summoner (id).

    ### Parameters
        summoner_id : `str`
            Pass a summoner id as a string to be updated

        region : `Region, optional`
            Pass the region you want to perform the update in. Default is "NA".

    ### Returns
        `dict` : Returns a dictionary with the status response.
            Example response:
        ```
        {
            'status': 202,
            'data': {
                'message': 'Already renewed.',
                'last_updated_at': '2024-07-13T10:06:11+09:00',
                'renewable_at': '2024-07-13T10:08:12+09:00'
            }
        }
        ```
    """

    res = requests.post(API_URL.format(region=region, summoner_id=summoner_id), headers=HEADERS)
    if not res.ok:
        res.raise_for_status()

    return res.json()


def get_page_props(summoner_names: str | list[str] = "ColbyFaulkn1", region=Region.NA) -> dict:
    """
    Get the page props from OPGG. (Contains data such as summoner info, champions, seasons, etc.)

    ### Parameters
        summoner_names : `str | list[str], optional`
            Pass a single or comma separated `str` or a list of summoner names.\n
            Note: Default is "abc", as this can be any valid summoner if you just want page props. (All champs, seasons, etc.)

        region : `Region, optional`
            Pass the region you want to search in. Default is "NA".

    ### Returns
        `dict` : Returns a dictionary with the page props.
    """

    if isinstance(summoner_names, list) and summoner_names:
        summoner_names = ",".join(summoner_names)

    url = f"https://www.op.gg/multisearch/{region}?summoners={summoner_names}"

    res = requests.get(url, headers=HEADERS, allow_redirects=True)
    soup = BeautifulSoup(res.content, "html.parser")

    try:
        return json.loads(soup.select_one("#__NEXT_DATA__").text)["props"]["pageProps"]

    except JSONDecodeError:
        return {}


def get_all_seasons(page_props=None) -> list[SeasonInfo]:
    """
    Get all seasons from OPGG.

    ### Args:
        region : `Region, optional`
            Pass the region you want to search in. Defaults to "NA".

        page_props : `dict, optional`
            Pass the page props if the program has queried them once before.\n
            Note: Defaults to None, but if you pass them it reduces the overhead of another request out to OPGG.

    ### Returns:
        `list[SeasonInfo]` : A list of SeasonInfo objects.
    """
    # Check cache, if found, return it, otherwise continue to below logic.
    cached_seasons = Cacher().get_all_seasons()
    if cached_seasons:
        return cached_seasons

    seasons = []

    # For seasons specifically, if page_props is not passed, we MUST use it.
    # I have not been able to find a seasons endpoint on the api yet.
    if page_props is None:
        page_props = get_page_props()

    for season in dict(page_props["seasonsById"]).values():
        if season:
            seasons.append(
                SeasonInfo(
                    id=season.get("id"),
                    value=season.get("value"),
                    display_value=season.get("display_value"),
                    split=season.get("split"),
                    is_preseason=season.get("is_preseason"),
                )
            )

    return seasons


def get_season_by(by: By, value: int | str | list) -> SeasonInfo | list[SeasonInfo]:
    """
    Get a season by a specific metric.

    ### Args:
        by : `By`
            Pass a By enum to specify how you want to get the season(s).

        value : `int | str | list`
            Pass the value(s) you want to search by. (id, display_value, etc.)

    ### Returns:
        `SeasonInfo | list[SeasonInfo]` : A single or list of SeasonInfo objects.
    """
    all_seasons = get_all_seasons()
    result_set = []

    if by == By.ID:
        if isinstance(value, list):
            for season in all_seasons:
                for _id in value:
                    if season.id == _id:
                        result_set.append(season)

        else:
            for season in all_seasons:
                if season.id == int(value):
                    result_set.append(season)

    # TODO: perhaps add more ways to get season objs, like by is_preseason, or display_name, etc.

    return result_set if len(result_set) > 1 else result_set[0]


def get_all_champions(page_props=None) -> list[Champion]:
    """
    Get all champion info from OPGG.

    ### Args:
        region : `Region, optional`
            Pass the region you want to search in. Defaults to "NA".

        page_props : `dict, optional`
            Pass the page props if the program has queried them once before.\n
            Note: Defaults to None, but if you pass them it reduces the overhead of another request out to OPGG.

    Returns:
        `list[Champion]` : A list of Champion objects.
    """
    # Check cache, if found, return it, otherwise continue to below logic.
    champions = []

    if not page_props:
        cached_champions = Cacher().get_all_champs()
        if cached_champions:
            return cached_champions

        res = requests.get(f"{BASE_API_URL}/meta/champions?hl=en_US", headers=HEADERS)
        try:
            raw_champs_data = json.loads(res.text)["data"]

        except JSONDecodeError:
            raw_champs_data = []

    else:
        raw_champs_data = dict(page_props["championsById"]).values()

    for champion in raw_champs_data:
        # reset per iteration
        spells = []
        skins = []

        for skin in champion.get("skins", []):
            prices = []

            for price in skin.get("prices", []):
                prices.append(
                    Price(
                        currency=price.get("currency") if "RP" in price.get("currency", "") else "BE",
                        cost=price.get("cost"),
                    )
                )

            skins.append(
                Skin(
                    id=skin.get("id"),
                    champion_id=skin.get("champion_id"),
                    name=skin.get("name"),
                    centered_image=skin.get("centered_image"),
                    skin_video_url=skin.get("skin_video_url"),
                    prices=prices,
                    release_date=datetime.fromisoformat(skin["release_date"]) if skin.get("release_date") else None,
                    sales=skin.get("sales"),
                )
            )

        for spell in champion.get("spells", []):
            spells.append(
                Spell(
                    key=spell.get("key"),
                    name=spell.get("name"),
                    description=spell.get("description"),
                    max_rank=spell.get("max_rank"),
                    range_burn=spell.get("range_burn"),
                    cooldown_burn=spell.get("cooldown_burn"),
                    cooldown_burn_float=spell.get("cooldown_burn_float"),
                    cost_burn=spell.get("cost_burn"),
                    tooltip=spell.get("tooltip"),
                    image_url=spell.get("image_url"),
                    video_url=spell.get("video_url"),
                )
            )

        champions.append(
            Champion(
                id=champion.get("id"),
                key=champion.get("key"),
                name=champion.get("name"),
                image_url=champion.get("image_url"),
                evolve=champion.get("evolve"),
                partype=champion.get("partype"),
                passive=Passive(
                    name=champion.get("passive", {}).get("name"),
                    description=champion.get("passive", {}).get("description"),
                    image_url=champion.get("passive", {}).get("image_url"),
                    video_url=champion.get("passive", {}).get("video_url"),
                ),
                spells=spells,
                skins=skins,
            )
        )

    return champions


def get_champion_by(by: By, value: int | str | list, **kwargs) -> Champion | list[Champion]:
    """
    Get a single or list of champions by a specific metric.

    ### Args:
        by : `By`
            Pass a By enum to specify how you want to get the champion(s).

        value : `int | str | list`
            Pass the value(s) you want to search by. (id, key, name, etc.)

        **kwargs : `any`
            Pass any additional keyword arguments to narrow down the search.\n
            Note: Currently only supports "currency" for the cost of a champion.\n

            Example:
                `get_champion_by(By.COST, 450, currency=By.BLUE_ESSENCE)`
    """
    # Currently kwargs only handles "currency" for the cost of a champion,
    # but I might introduce other metrics of getting champ objs later, idk...

    if kwargs.get("page_props"):
        all_champs = get_all_champions(page_props=kwargs["page_props"])

    else:
        all_champs = get_all_champions()

    result_set = []
    if by == By.ID:
        if isinstance(value, list):
            for champ in all_champs:
                for _id in value:
                    if champ.id == _id:
                        result_set.append(champ)

        else:
            for champ in all_champs:
                if champ.id == int(value):
                    result_set.append(champ)

    elif by == By.KEY:
        if isinstance(value, list):
            for champ in all_champs:
                for key in value:
                    if champ.key == key:
                        result_set.append(champ)
        else:
            for champ in all_champs:
                if champ.key == value:
                    result_set.append(champ)

    elif by == By.NAME:
        if isinstance(value, list):
            for champ in all_champs:
                for name in value:
                    if champ.name == name:
                        result_set.append(champ)

        else:
            for champ in all_champs:
                if champ.name == value:
                    result_set.append(champ)

    elif by == By.COST:
        for champ in all_champs:
            if champ.skins[0].prices:
                for price in champ.skins[0].prices:
                    if str(kwargs.get("currency", "")).upper() == price.currency and price.cost in value:
                        result_set.append(champ)

    # if the result set is larger than one, return the whole list, otherwise just return the object itself.
    return result_set if len(result_set) > 1 else result_set[0]
