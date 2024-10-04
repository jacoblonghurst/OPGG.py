# Quick and simple scraper to pull some data from OPGG using multisearch

# Author  : ShoobyDoo
# Date    : 2023-07-05
# License : BSD-3-Clause

# fmt: off
import os
import sys
import json
import logging
import traceback
from typing import Literal
from datetime import datetime
from json import JSONDecodeError

import requests
from fake_useragent import UserAgent

from opgg.cacher import Cacher
from opgg.params import Region
from opgg.game import GameStats, Stats, Team
from opgg.champion import ChampionStats, Champion
from opgg.season import RankEntry, Season, SeasonInfo
from opgg.summoner import Game, Participant, Summoner
from opgg.league_stats import LeagueStats, Tier, QueueInfo
from opgg.utils import get_page_props, get_all_seasons, get_all_champions


# fmt: on


class OPGG:
    """
    ### OPGG.py
    A simple library to access and structure the data from OP.GG's Website & API.

    Copyright (c) 2023-2024, ShoobyDoo
    License: BSD-3-Clause, See LICENSE for more details.
    """

    __author__ = "ShoobyDoo"
    __license__ = "BSD-3-Clause"

    cached_page_props = None

    # Todo: Add support for the following endpoint(s):
    # https://op.gg/api/v1.0/internal/bypass/games/na/summoners/<summoner_id?>/?&limit=20&hl=en_US&game_type=total

    # HUGE find. Incorporate the following endpoint:
    # https://op.gg/api/v1.0/internal/bypass/meta/champions/<champion_id>?hl=<lang_code>

    # METADATA FOR CHAMPIONS -- USE THIS OVER PAGE_PROPS.
    # https://op.gg/api/v1.0/internal/bypass/meta/champions?hl=en_US

    def __init__(self, summoner_id: str | None = None, region=Region.NA) -> None:
        self._summoner_id = summoner_id
        self._region = region

        self._base_api_url = "https://lol-web-api.op.gg/api/v1.0/internal/bypass"
        self._api_url = f"{self._base_api_url}/summoners/{self.region}/{self.summoner_id}/summary"
        self._games_api_url = f"{self._base_api_url}/games/{self.region}/summoners/{self.summoner_id}"

        self._ua = UserAgent()
        self._headers = {"User-Agent": self._ua.random}

        self._all_champions = None
        self._all_seasons = None

        # ===== SETUP START =====
        logging.root.name = "OPGG.py"

        if not os.path.exists("./logs"):
            logging.info("Creating logs directory...")
            os.mkdir("./logs")
        else:
            # remove empty log files
            for file in os.listdir("./logs"):
                if os.stat(f"./logs/{file}").st_size == 0 and file != f'opgg_{datetime.now().strftime("%Y-%m-%d")}.log':
                    logging.info(f"Removing empty log file: {file}")
                    os.remove(f"./logs/{file}")

        logging.basicConfig(
            filename=f'./logs/opgg_{datetime.now().strftime("%Y-%m-%d")}.log',
            filemode="a+",
            format="[%(asctime)s][%(name)s->%(module)s:%(lineno)-10d][%(levelname)-7s] : %(message)s",
            datefmt="%d-%b-%y %H:%M:%S",
            level=logging.INFO,
        )
        # ===== SETUP END =====

        # allow the user to interact with the logger
        self._logger = logging.getLogger("OPGG.py")

        # at object creation, setup and query the cache
        self._cacher = Cacher()
        self._cacher.setup()

        self.logger.info(
            f"OPGG.__init__(summoner_id={self.summoner_id}, "
            f"region={self.region}, "
            f"api_url={self.api_url}, "
            f"headers={self.headers}, "
            f"all_champions={self.all_champions}, "
            f"all_seasons={self.all_seasons})"
        )

    @property
    def logger(self) -> logging.Logger:
        """
        A `Logger` object representing the logger instance.

        The logging level is set to `INFO` by default.
        """
        return self._logger

    @property
    def summoner_id(self) -> str:
        """
        A `str` representing the summoner id. (Riot API)
        """
        return self._summoner_id

    @summoner_id.setter
    def summoner_id(self, value: str) -> None:
        self._summoner_id = value
        self.refresh_api_url()

    @property
    def region(self) -> str:
        """
        A `str` representing the region to search in.
        """
        return self._region

    @region.setter
    def region(self, value: str) -> None:
        self._region = value
        self.refresh_api_url()

    @property
    def api_url(self) -> str:
        """
        A `str` representing the api url to send requests to. (OPGG API)
        """
        return self._api_url

    @api_url.setter
    def api_url(self, value: str) -> None:
        self._api_url = value

    @property
    def headers(self) -> dict:
        """
        A `dict` representing the headers to send with the request.
        """
        return self._headers

    @headers.setter
    def headers(self, value: dict) -> None:
        self._headers = value

    @property
    def all_champions(self) -> list[Champion]:
        """
        A `list[Champion]` objects representing all champions in the game.
        """
        return self._all_champions

    @all_champions.setter
    def all_champions(self, value: list[Champion]) -> None:
        self._all_champions = value

    @property
    def all_seasons(self) -> list[SeasonInfo]:
        """
        A `list[SeasonInfo]` objects representing all seasons in the game.
        """
        return self._all_seasons

    @all_seasons.setter
    def all_seasons(self, value: list[SeasonInfo]) -> None:
        self._all_seasons = value

    @property
    def cacher(self) -> Cacher:
        """
        A `Cacher` object representing the summoner_id cacher.
        """
        return self._cacher

    def refresh_api_url(self) -> None:
        """
        A method to refresh the api url with the current summoner id and region.
        """
        self.api_url = f"{self._base_api_url}/summoners/{self.region}/{self.summoner_id}/summary"
        self._games_api_url = f"{self._base_api_url}/games/{self.region}/summoners/{self.summoner_id}"

        self.logger.debug(f"self.refresh_api_url() called... See URLs:")
        self.logger.debug(f"self.api_url = {self.api_url}")
        self.logger.debug(f"self._games_api_url = {self._games_api_url}")

    def get_summoner(self, return_content_only=False) -> Summoner | dict:
        """
        A method to get data from the OPGG API and form a Summoner object.

        General flow:\n
            -> Send request to OPGG API\n
            -> Parse data from request (jsonify)\n
            -> Loop through data and form the summoner object.

        ### Returns:
            `Summoner`: A Summoner object representing the summoner.
        """
        self.logger.info(f"Sending request to OPGG API... (API_URL = {self.api_url}, HEADERS = {self.headers})")
        res = requests.get(self.api_url, headers=self.headers)

        previous_seasons: list[Season] = []
        league_stats: list[LeagueStats] = []
        most_champions: list[ChampionStats] = []
        recent_game_stats: list[Game] = []

        content = None
        if res.ok:
            self.logger.info(f"Request to OPGG API was successful, parsing data (Content Length: {len(res.text)})...")
            self.logger.debug(f"SUMMONER DATA AT /SUMMARY ENDPOINT:\n{res.text}\n")
            try:
                content = json.loads(res.text).get("data", [])
                # If return_res is passed in func args, return the content
                # Required in tests to get all the raw content without building the summoner object
                if return_content_only:
                    return content

                if not content:
                    self.logger.error("No data returned from the API.")
                    return content

            except (TypeError, json.JSONDecodeError):
                self.logger.error(f"Failed to decode json data")
                # todo: figure out what to return here once i've seen what else this is calling
                sys.exit(1)

        else:
            res.raise_for_status()

        try:
            for season in content.get("summoner", {}).get("previous_seasons", []):  # type: dict
                tmp_season_info = None
                if self.all_seasons:
                    for _season in self.all_seasons:
                        if _season.id == season.get("season_id", -1):
                            tmp_season_info = _season
                            break

                tmp_rank_entries = []
                for rank_entry in season.get("rank_entries", []):
                    if rank_entry.get("rank_info") is None:
                        continue

                    tmp_rank_entries.append(
                        RankEntry(
                            game_type=rank_entry.get("game_type"),
                            rank_info=Tier(
                                tier=rank_entry.get("rank_info", {}).get("tier"),
                                division=rank_entry.get("rank_info", {}).get("division"),
                                lp=rank_entry.get("rank_info", {}).get("lp"),
                            ),
                            created_at=(
                                datetime.fromisoformat(rank_entry["created_at"]) if rank_entry["created_at"] else None
                            ),
                        )
                    )

                previous_seasons.append(
                    Season(
                        season_id=tmp_season_info.id,  # looks like this should have been .id
                        tier_info=Tier(
                            tier=season.get("tier_info", {}).get("tier"),
                            division=season.get("tier_info", {}).get("division"),
                            lp=season.get("tier_info", {}).get("lp"),
                            tier_image_url=season.get("tier_info", {}).get("tier_image_url"),
                            border_image_url=season.get("tier_info", {}).get("border_image_url"),
                        ),
                        rank_entries=tmp_rank_entries,
                        created_at=datetime.fromisoformat(season["created_at"]) if season["created_at"] else None,
                    )
                )

            for league in content.get("summoner", {}).get("league_stats"):
                tier_info = league.get("tier_info", {})
                league_stats.append(
                    LeagueStats(
                        queue_info=QueueInfo(
                            id=league.get("queue_info", {}).get("id"),
                            queue_translate=league.get("queue_info", {}).get("queue_translate"),
                            game_type=league.get("queue_info", {}).get("game_type"),
                        ),
                        tier_info=Tier(
                            tier=tier_info.get("tier"),
                            division=tier_info.get("division"),
                            lp=tier_info.get("lp"),
                            tier_image_url=tier_info.get("tier_image_url"),
                            border_image_url=tier_info.get("border_image_url"),
                            level=tier_info.get("level"),
                        ),
                        win=league.get("win"),
                        lose=league.get("lose"),
                        is_hot_streak=league.get("is_hot_streak"),
                        is_fresh_blood=league.get("is_fresh_blood"),
                        is_veteran=league.get("is_veteran"),
                        is_inactive=league.get("is_inactive"),
                        series=league.get("series"),
                        updated_at=league.get("updated_at"),
                    )
                )

            for champion in content.get("summoner", {}).get("most_champions", {}).get("champion_stats", []):
                tmp_champ = None
                if self.all_champions:
                    for _champion in self.all_champions:
                        if _champion.id == champion.get("id", -1):
                            tmp_champ = _champion
                            break

                most_champions.append(
                    ChampionStats(
                        champion=tmp_champ,
                        id=champion.get("id"),
                        play=champion.get("play"),
                        win=champion.get("win"),
                        lose=champion.get("lose"),
                        kill=champion.get("kill"),
                        death=champion.get("death"),
                        assist=champion.get("assist"),
                        gold_earned=champion.get("gold_earned"),
                        minion_kill=champion.get("minion_kill"),
                        turret_kill=champion.get("turret_kill"),
                        neutral_minion_kill=champion.get("neutral_minion_kill"),
                        damage_dealt=champion.get("damage_dealt"),
                        damage_taken=champion.get("damage_taken"),
                        physical_damage_dealt=champion.get("physical_damage_dealt"),
                        magic_damage_dealt=champion.get("magic_damage_dealt"),
                        most_kill=champion.get("most_kill"),
                        max_kill=champion.get("max_kill"),
                        max_death=champion.get("max_death"),
                        double_kill=champion.get("double_kill"),
                        triple_kill=champion.get("triple_kill"),
                        quadra_kill=champion.get("quadra_kill"),
                        penta_kill=champion.get("penta_kill"),
                        game_length_second=champion.get("game_length_second"),
                        inhibitor_kills=champion.get("inhibitor_kills"),
                        sight_wards_bought_in_game=champion.get("sight_wards_bought_in_game"),
                        vision_wards_bought_in_game=champion.get("vision_wards_bought_in_game"),
                        vision_score=champion.get("vision_score"),
                        wards_placed=champion.get("wards_placed"),
                        wards_killed=champion.get("wards_killed"),
                        heal=champion.get("heal"),
                        time_ccing_others=champion.get("time_ccing_others"),
                        op_score=champion.get("op_score"),
                        is_max_in_team_op_score=champion.get("is_max_in_team_op_score"),
                        physical_damage_taken=champion.get("physical_damage_taken"),
                        damage_dealt_to_champions=champion.get("damage_dealt_to_champions"),
                        physical_damage_dealt_to_champions=champion.get("physical_damage_dealt_to_champions"),
                        magic_damage_dealt_to_champions=champion.get("magic_damage_dealt_to_champions"),
                        damage_dealt_to_objectives=champion.get("damage_dealt_to_objectives"),
                        damage_dealt_to_turrets=champion.get("damage_dealt_to_turrets"),
                        damage_self_mitigated=champion.get("damage_self_mitigated"),
                        max_largest_multi_kill=champion.get("max_largest_multi_kill"),
                        max_largest_critical_strike=champion.get("max_largest_critical_strike"),
                        max_largest_killing_spree=champion.get("max_largest_killing_spree"),
                        snowball_throws=champion.get("snowball_throws"),
                        snowball_hits=champion.get("snowball_hits"),
                    )
                )

            # page props did not return any recent games, lets query the /games endpoint instead
            # gets the summoner id from the objects internal self._game_api_url's self.summoner_id ref
            recent_game_stats: Game | list[Game] = self.get_recent_games()

        except Exception:
            self.logger.error(
                f"Error parsing some summoner data... (Could be that they just come in as nulls...): {traceback.format_exc()}"
            )

        return Summoner(
            id=content.get("summoner", {}).get("id"),
            summoner_id=content.get("summoner", {}).get("summoner_id"),
            acct_id=content.get("summoner", {}).get("acct_id"),
            puuid=content.get("summoner", {}).get("puuid"),
            game_name=content.get("summoner", {}).get("game_name"),
            tagline=content.get("summoner", {}).get("tagline"),
            name=content.get("summoner", {}).get("name"),
            internal_name=content.get("summoner", {}).get("internal_name"),
            profile_image_url=content.get("summoner", {}).get("profile_image_url"),
            level=content.get("summoner", {}).get("level"),
            updated_at=content.get("summoner", {}).get("updated_at"),
            renewable_at=content.get("summoner", {}).get("renewable_at"),
            previous_seasons=previous_seasons,
            league_stats=league_stats,
            most_champions=most_champions,
            recent_game_stats=recent_game_stats,
        )

    def search(self, summoner_names: str | list[str], region=Region.NA) -> Summoner | list[Summoner] | str:
        """
        Search for a single or multiple summoner(s) on OPGG.

        ### Args:
            summoner_names : `str` | `list[str]`
                Pass either a `str` (comma seperated) or `list[str]` of summoner names + regional identifier (#NA1, #EUW, etc).

            region : `Region, optional`
                Pass the region you want to search in. Defaults to "NA".

        ### Returns:
            `list[Summoner]` | `str` : A single or list of Summoner objects, or a string if no summoner(s) were found.
        """

        if isinstance(summoner_names, str):
            if "," in summoner_names:
                summoner_names = summoner_names.split(",")

            else:
                summoner_names = [summoner_names]

        # General flow of cache retrieval:
        # 1. Pull from cache db
        #   -> If found, add to list of cached summoner ids, and below iterate over and set the summoner id property
        #   -> As an extension of the above, these requests would go directly to the api to pull summary/full data
        #   -> If not found, add to list of summoner names to query
        # 2. Build the summoner objects accordingly
        cached_summoner_ids = []
        uncached_summoners = []

        # TODO: Cache get/set logic needs to be reworked to account for regional identifiers. Currently, you could have 2 of the same users on different regions and the cache will just return whatever the first entry that was cached would've been. This is not ideal, perhaps I should force people to append the regional identifiers? This would result in unique entries in the cache...
        for summoner_name in summoner_names:
            if "#" not in summoner_name:
                raise Exception(
                    f'No regional identifier was found for query: "{summoner_name}". Please include the identifier as well and try again. (#NA1, #EUW, etc.)'
                )

            cached_id = self.cacher.get_summoner_id(summoner_name)
            if cached_id:
                cached_summoner_ids.append(cached_id)

            else:
                uncached_summoners.append(summoner_name)

        # pass only uncached summoners to get_page_props()
        page_props = get_page_props(uncached_summoners, region)

        self.logger.debug(f"\n********PAGE_PROPS_START********\n{page_props}\n********PAGE_PROPS_STOP********")

        if len(uncached_summoners) > 0:
            self.logger.info(
                f"No cache for {len(uncached_summoners)} summoners: {uncached_summoners}, fetching... (using get_page_props() site scraper)"
            )

        if len(cached_summoner_ids) > 0:
            self.logger.info(
                f"Cache found for {len(cached_summoner_ids)} summoners: {cached_summoner_ids}, fetching... (using get_summoner() api)"
            )

        # Query cache for champs and seasons
        cached_seasons = self.cacher.get_all_seasons()
        cached_champions = self.cacher.get_all_champs()

        # If we found some cached seasons/champs, use them, otherwise fetch and cache them.
        if cached_seasons:
            self.all_seasons = cached_seasons
        else:
            self.all_seasons = get_all_seasons(page_props)
            self.cacher.insert_all_seasons(self.all_seasons)

        if cached_champions:
            self.all_champions = cached_champions
        else:
            self.all_champions = get_all_champions(page_props)
            self.cacher.insert_all_champs(self.all_champions)

        # todo: if more than 5 summoners are passed, break into 5s and iterate over each set
        # note: this would require calls to the refresh_api_url() method each iteration?

        # set the region to the passed one. this is what get_summoner() relies on
        self.region = region

        # bit of weirdness around generic usernames. If you pass "abc" for example, it will return multiple summoners in the page props.
        # To help, we will check against opgg's "internal_name" property, which seems to be the username.lower() with spaces removed.
        summoners = []
        for summoner_name in summoner_names:
            # if there are multiple search results for a SINGLE summoner_name, query MUST include the regional identifier
            if len(page_props.get("summoners", [])) > 1 and "#" in summoner_name:
                logging.debug(f"MULTI-RESULT | page_props->summoners: {page_props.get('summoners')}")
                only_summoner_name, only_region = summoner_name.split("#")
                for summoner in page_props.get("summoners", []):
                    if only_summoner_name.strip() == summoner.get(
                        "game_name", ""
                    ) and only_region.strip() == summoner.get("tagline", ""):
                        self.summoner_id = summoner.get("summoner_id", "")
                        break

            elif len(page_props.get("summoners", [])) > 1 and "#" not in summoner_name:
                raise Exception(
                    f'Multiple search results were returned for "{summoner_name}". Please include the identifier as well and try again. (#NA1, #EUW, etc.)'
                )

            elif len(page_props.get("summoners", [])) == 1:
                self.summoner_id = page_props["summoners"][0]["summoner_id"]

            summoner = self.get_summoner()
            summoners.append(summoner)
            self.logger.info(f"Summoner object built for: {summoner.name} ({summoner.summoner_id}), caching...")
            self.cacher.insert_summoner(summoner.name, summoner.summoner_id)

        # cached summoners go straight to api
        for _cached_summoner_id in cached_summoner_ids:
            self.summoner_id = _cached_summoner_id
            summoner = self.get_summoner()
            summoners.append(summoner)
            self.logger.info(f"Summoner object built for: {summoner.name} ({summoner.summoner_id})")

        # todo: add custom exceptions instead of this.
        # todo: raise SummonerNotFound exception
        if len(summoners) == 0:
            raise Exception(f"No summoner(s) matching {summoner_names} were found...")

        return summoners if len(summoners) > 1 else summoners[0]

    def get_recent_games(
        self, results: int = 10, game_type: Literal["total", "ranked", "normal"] = "total", return_content_only=False
    ) -> list[dict] | list[Game]:
        recent_games = []
        res = requests.get(f"{self._games_api_url}?&limit={results}&game_type={game_type}", headers=self.headers)

        self.logger.debug(res.text)
        game_data = []
        if res.ok:
            self.logger.info(
                f"Request to OPGG GAME_API was successful, parsing data (Content Length: {len(res.text)})..."
            )
            try:
                game_data: list[dict] = json.loads(res.text).get("data", [])
                if return_content_only:
                    return game_data

                if not game_data:
                    return game_data

            except (TypeError, JSONDecodeError):
                self.logger.error(f"Failed to decode json data")
                # todo: figure out what to return here once i've seen what else this is calling
                sys.exit(1)

        else:
            res.raise_for_status()

        try:
            for game in game_data:
                participants = []
                for participant in game.get("participants", []):
                    psum = participant.get("summoner", {})
                    pstats = participant.get("stats", {})
                    participants.append(
                        Participant(
                            summoner=Summoner(
                                id=psum.get("id"),
                                summoner_id=psum.get("summoner_id"),
                                acct_id=psum.get("acct_id"),
                                puuid=psum.get("puuid"),
                                game_name=psum.get("game_name"),
                                tagline=psum.get("tagline"),
                                name=psum.get("name"),
                                internal_name=psum.get("internal_name"),
                                profile_image_url=psum.get("profile_image_url"),
                                level=psum.get("level"),
                                updated_at=psum.get("updated_at"),
                                renewable_at=psum.get("renewable_at"),
                            ),
                            participant_id=participant.get("participant_id"),
                            champion_id=participant.get("champion_id"),
                            team_key=participant.get("team_key"),
                            position=participant.get("position"),
                            role=participant.get("role"),
                            items=participant.get("items"),
                            trinket_item=participant.get("trinket_item"),
                            rune=None,
                            # rune={
                            #    participant["rune"]["primary_page_id"],
                            #    participant["rune"]["primary_rune_id"],
                            #    participant["rune"]["secondary_page_id"],
                            # },  # temp, eventually turn this into an object..?
                            spells=participant.get("spells"),
                            stats=Stats(
                                champion_level=pstats.get("champion_level"),
                                damage_self_mitigated=pstats.get("damage_self_mitigated"),
                                damage_dealt_to_objectives=pstats.get("damage_dealt_to_objectives"),
                                damage_dealt_to_turrets=pstats.get("damage_dealt_to_turrets"),
                                magic_damage_dealt_player=pstats.get("magic_damage_dealt_player"),
                                physical_damage_taken=pstats.get("physical_damage_taken"),
                                physical_damage_dealt_to_champions=pstats.get("physical_damage_dealt_to_champions"),
                                total_damage_taken=pstats.get("total_damage_taken"),
                                total_damage_dealt=pstats.get("total_damage_dealt"),
                                total_damage_dealt_to_champions=pstats.get("total_damage_dealt_to_champions"),
                                largest_critical_strike=pstats.get("largest_critical_strike"),
                                time_ccing_others=pstats.get("time_ccing_others"),
                                vision_score=pstats.get("vision_score"),
                                vision_wards_bought_in_game=pstats.get("vision_wards_bought_in_game"),
                                sight_wards_bought_in_game=pstats.get("sight_wards_bought_in_game"),
                                ward_kill=pstats.get("ward_kill"),
                                ward_place=pstats.get("ward_place"),
                                turret_kill=pstats.get("champion_level"),
                                barrack_kill=pstats.get("barrack_kill"),
                                kill=pstats.get("kill"),
                                death=pstats.get("death"),
                                assist=pstats.get("assist"),
                                largest_multi_kill=pstats.get("largest_multi_kill"),
                                largest_killing_spree=pstats.get("largest_killing_spree"),
                                minion_kill=pstats.get("minion_kill"),
                                neutral_minion_kill_team_jungle=pstats.get("neutral_minion_kill_team_jungle"),
                                neutral_minion_kill_enemy_jungle=pstats.get("neutral_minion_kill_enemy_jungle"),
                                neutral_minion_kill=pstats.get("neutral_minion_kill"),
                                gold_earned=pstats.get("gold_earned"),
                                total_heal=pstats.get("total_heal"),
                                result=pstats.get("result"),
                                op_score=pstats.get("op_score"),
                                op_score_rank=pstats.get("op_score_rank"),
                                is_opscore_max_in_team=pstats.get("is_opscore_max_in_team"),
                                lane_score=pstats.get("lane_score"),
                                op_score_timeline=pstats.get("op_score_timeline"),
                                op_score_timeline_analysis=pstats.get("op_score_timeline_analysis"),
                            ),
                            tier_info=Tier(
                                tier=participant.get("tier_info", {}).get("tier"),
                                division=participant.get("tier_info", {}).get("division"),
                                lp=participant.get("tier_info", {}).get("lp"),
                                level=participant.get("tier_info", {}).get("level"),
                                tier_image_url=participant.get("tier_info", {}).get("tier_image_url"),
                                border_image_url=participant.get("tier_info", {}).get("border_image_url"),
                            ),
                        )
                    )

                teams = []
                for team in game.get("teams", []):
                    game_stats = team.get("game_stat", {})
                    teams.append(
                        Team(
                            key=team["key"],
                            game_stat=GameStats(
                                is_win=game_stats.get("is_win"),
                                champion_kill=game_stats.get("champion_kill"),
                                champion_first=game_stats.get("champion_first"),
                                inhibitor_kill=game_stats.get("inhibitor_kill"),
                                inhibitor_first=game_stats.get("inhibitor_first"),
                                rift_herald_kill=game_stats.get("rift_herald_kill"),
                                rift_herald_first=game_stats.get("rift_herald_first"),
                                dragon_kill=game_stats.get("dragon_kill"),
                                dragon_first=game_stats.get("dragon_first"),
                                baron_kill=game_stats.get("baron_kill"),
                                baron_first=game_stats.get("baron_first"),
                                tower_kill=game_stats.get("tower_kill"),
                                tower_first=game_stats.get("tower_first"),
                                horde_kill=game_stats.get("horde_kill"),
                                horde_first=game_stats.get("horde_first"),
                                is_remake=game_stats.get("is_remake"),
                                death=game_stats.get("death"),
                                assist=game_stats.get("assist"),
                                gold_earned=game_stats.get("gold_earned"),
                                kill=game_stats.get("kill"),
                            ),
                            banned_champions=team.get("banned_champions"),
                        )
                    )

                my_data = game.get("myData", {})
                tmp_game = Game(
                    id=game.get("id"),
                    created_at=game.get("created_at"),
                    game_map=game.get("game_map"),
                    queue_info=QueueInfo(
                        id=game.get("queue_info", {}).get("id"),
                        queue_translate=game.get("queue_info", {}).get("queue_translate"),
                        game_type=game.get("queue_info", {}).get("game_type"),
                    ),
                    version=game.get("version"),
                    game_length_second=game.get("game_length_second"),
                    is_remake=game.get("is_remake"),
                    is_opscore_active=game.get("is_opscore_active"),
                    is_recorded=game.get("is_recorded"),
                    record_info=game.get("record_info"),
                    average_tier_info=Tier(
                        tier=game.get("average_tier_info", {}).get("tier"),
                        division=game.get("average_tier_info", {}).get("division"),
                        tier_image_url=game.get("average_tier_info", {}).get("tier_image_url"),
                        border_image_url=game.get("average_tier_info", {}).get("border_image_url"),
                    ),
                    participants=participants,
                    teams=teams,
                    memo=game.get("memo"),
                    my_data=Participant(
                        summoner=Summoner(
                            id=my_data.get("summoner", {}).get("id"),
                            summoner_id=my_data.get("summoner", {}).get("summoner_id"),
                            acct_id=my_data.get("summoner", {}).get("acct_id"),
                            puuid=my_data.get("summoner", {}).get("puuid"),
                            game_name=my_data.get("summoner", {}).get("game_name"),
                            tagline=my_data.get("summoner", {}).get("tagline"),
                            name=my_data.get("summoner", {}).get("name"),
                            internal_name=my_data.get("summoner", {}).get("internal_name"),
                            profile_image_url=my_data.get("summoner", {}).get("profile_image_url"),
                            level=my_data.get("summoner", {}).get("level"),
                            updated_at=my_data.get("summoner", {}).get("updated_at"),
                            renewable_at=my_data.get("summoner", {}).get("renewable_at"),
                        ),
                        participant_id=my_data.get("participant_id"),
                        champion_id=my_data.get("champion_id"),
                        team_key=my_data.get("team_key"),
                        position=my_data.get("position"),
                        role=my_data.get("role"),
                        items=my_data.get("items"),
                        trinket_item=my_data.get("trinket_item"),
                        rune=None,
                        # rune={
                        #     game["myData"]["rune"]["primary_page_id"],
                        #     game["myData"]["rune"]["primary_rune_id"],
                        #     game["myData"]["rune"]["secondary_page_id"],
                        # },  # temp, eventually turn this into an object..?
                        spells=my_data.get("spells"),
                        stats=Stats(
                            champion_level=my_data.get("stats", {}).get("champion_level"),
                            damage_self_mitigated=my_data.get("stats", {}).get("damage_self_mitigated"),
                            damage_dealt_to_objectives=my_data.get("stats", {}).get("damage_dealt_to_objectives"),
                            damage_dealt_to_turrets=my_data.get("stats", {}).get("damage_dealt_to_turrets"),
                            magic_damage_dealt_player=my_data.get("stats", {}).get("magic_damage_dealt_player"),
                            physical_damage_taken=my_data.get("stats", {}).get("physical_damage_taken"),
                            physical_damage_dealt_to_champions=my_data.get("stats", {}).get(
                                "physical_damage_dealt_to_champions"
                            ),
                            total_damage_taken=my_data.get("stats", {}).get("total_damage_taken"),
                            total_damage_dealt=my_data.get("stats", {}).get("total_damage_dealt"),
                            total_damage_dealt_to_champions=my_data.get("stats", {}).get(
                                "total_damage_dealt_to_champions"
                            ),
                            largest_critical_strike=my_data.get("stats", {}).get("largest_critical_strike"),
                            time_ccing_others=my_data.get("stats", {}).get("time_ccing_others"),
                            vision_score=my_data.get("stats", {}).get("vision_score"),
                            vision_wards_bought_in_game=my_data.get("stats", {}).get("vision_wards_bought_in_game"),
                            sight_wards_bought_in_game=my_data.get("stats", {}).get("sight_wards_bought_in_game"),
                            ward_kill=my_data.get("stats", {}).get("ward_kill"),
                            ward_place=my_data.get("stats", {}).get("ward_place"),
                            turret_kill=my_data.get("stats", {}).get("champion_level"),
                            barrack_kill=my_data.get("stats", {}).get("barrack_kill"),
                            kill=my_data.get("stats", {}).get("kill"),
                            death=my_data.get("stats", {}).get("death"),
                            assist=my_data.get("stats", {}).get("assist"),
                            largest_multi_kill=my_data.get("stats", {}).get("largest_multi_kill"),
                            largest_killing_spree=my_data.get("stats", {}).get("largest_killing_spree"),
                            minion_kill=my_data.get("stats", {}).get("minion_kill"),
                            neutral_minion_kill_team_jungle=my_data.get("stats", {}).get(
                                "neutral_minion_kill_team_jungle"
                            ),
                            neutral_minion_kill_enemy_jungle=my_data.get("stats", {}).get(
                                "neutral_minion_kill_enemy_jungle"
                            ),
                            neutral_minion_kill=my_data.get("stats", {}).get("neutral_minion_kill"),
                            gold_earned=my_data.get("stats", {}).get("gold_earned"),
                            total_heal=my_data.get("stats", {}).get("total_heal"),
                            result=my_data.get("stats", {}).get("result"),
                            op_score=my_data.get("stats", {}).get("op_score"),
                            op_score_rank=my_data.get("stats", {}).get("op_score_rank"),
                            is_opscore_max_in_team=my_data.get("stats", {}).get("is_opscore_max_in_team"),
                            lane_score=my_data.get("stats", {}).get("lane_score"),
                            op_score_timeline=my_data.get("stats", {}).get("op_score_timeline"),
                            op_score_timeline_analysis=my_data.get("stats", {}).get("op_score_timeline_analysis"),
                        ),
                        tier_info=Tier(
                            tier=my_data.get("tier_info", {}).get("tier"),
                            division=my_data.get("tier_info", {}).get("division"),
                            lp=my_data.get("tier_info", {}).get("lp"),
                            level=my_data.get("tier_info", {}).get("level"),
                            tier_image_url=my_data.get("tier_info", {}).get("tier_image_url"),
                            border_image_url=my_data.get("tier_info", {}).get("border_image_url"),
                        ),
                    ),
                )

                recent_games.append(tmp_game)

            return recent_games

        except:
            self.logger.error(f"Unable to create game object, see trace: \n{traceback.format_exc()}")
            pass
