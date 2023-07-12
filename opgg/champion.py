# Quick and simple scraper to pull some data from OPGG using multisearch

# Author  : Doomlad
# Date    : 2023-07-05
# Edit    : 2023-07-09
# License : BSD-3-Clause


class Passive:
    def __init__(self,
                 name: str,
                 description: str,
                 image_url: str,
                 video_url: str) -> None:
        self._name = name
        self._description = description 
        self._image_url = image_url
        self._video_url = video_url

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def image_url(self) -> str:
        return self._image_url
    
    @property
    def video_url(self) -> str:
        return self._video_url
    

class Spell:
    def __init__(self,
                 key: str,
                 name: str,
                 description: str,
                 max_rank: int,
                 range_burn: list,
                 cooldown_burn: list,
                 cost_burn: list,
                 tooltip: str,
                 image_url: str,
                 video_url: str) -> None:
        self._key = key
        self._name = name
        self._description = description
        self._max_rank = max_rank
        self._range_burn = range_burn
        self._cooldown_burn = cooldown_burn
        self._cost_burn = cost_burn
        self._tooltip = tooltip
        self._image_url = image_url
        self._video_url = video_url

    @property
    def key(self) -> str:
        return self._key
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def max_rank(self) -> int:
        return self._max_rank
    
    @property
    def range_burn(self) -> list:
        return self._range_burn
    
    @property
    def cooldown_burn(self) -> list:
        return self._cooldown_burn
    
    @property
    def cost_burn(self) -> list:
        return self._cost_burn
    
    @property
    def tooltip(self) -> str:
        return self._tooltip
    
    @property
    def image_url(self) -> str:
        return self._image_url
    
    @property
    def video_url(self) -> str:
        return self._video_url
    
    def __repr__(self) -> str:
        return f"Skill({self.key}: {self.name})"


class Price:
    def __init__(self,
                 currency: str,
                 cost: int) -> None:
        self._currency = currency
        self._cost = cost
    
    @property
    def currency(self) -> str:
        return self._currency
    
    @property
    def cost(self) -> int:
        return self._cost
    
    def __repr__(self) -> str:
        return f"Price({self.currency}: {self.cost})"

class Skin:
    def __init__(self,
                 id: int,
                 name: str,
                 centered_image: str,
                 skin_video_url: str, 
                 prices: list[Price],
                 sales = None) -> None:
        self._id = id
        self._name = name
        self._centered_image = centered_image 
        self._skin_video_url = skin_video_url 
        self._prices = prices 
        self._sales = sales
    
    @property
    def id(self) -> int:
        return self._id
     
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def centered_image(self) -> str:
        return self._centered_image
     
    @property
    def skin_video_url(self) -> str:
        return self._skin_video_url
    
    @property
    def prices(self) -> list[Price]:
        return self._prices
    
    @property
    def sales(self) -> list:
        return self._sales         
    
    def __repr__(self) -> str:
        return f"Skin({self.name})"

class Champion:
    def __init__(self,
                 id: int,
                 key: str,
                 name: str,
                 image_url: str,
                 evolve: list,
                 passive: Passive,
                 spells: list[Spell],
                 skins: list[Skin]) -> None:
        self._id = id
        self._key = key
        self._name = name
        self._image_url = image_url
        self._evolve = evolve
        self._passive = passive
        self._spells = spells
        self._skins = skins
        
    @property
    def id(self) -> int:
        return self._id
     
    @property
    def key(self) -> str:
        return self._key
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def image_url(self) -> str:
        return self._image_url
    
    @property
    def evolve(self) -> list:
        return self._evolve
    
    @property
    def passive(self) -> Passive:
        return self._passive
    
    @property
    def spells(self) -> list[Spell]:
        return self._spells
    
    @property
    def skins(self) -> list[Skin]:
        return self._skins

    def get_cost_in(self, metric = "BE") -> int | None:
        # Get the cost of the champion in either blue essence or riot points
        metric = "IP" if metric == "BE" else metric.upper()
        
        for skin in self.skins:
            if skin.prices is not None:
                for price in skin.prices:
                    if price.currency == metric:
                        return price.cost
            else:
                return None
        
        
    def __repr__(self) -> str:
        return f"Champion(id={self.id}, name={self.name}, cost_be={self.get_cost_in()}, cost_rp={self.get_cost_in('rp')})"


class ChampionStats:
    def __init__(self,
                 id,
                 play,
                 win,
                 lose,
                 kill,
                 death,
                 assist,
                 gold_earned,
                 minion_kill,
                 turret_kill,
                 neutral_minion_kill,
                 damage_dealt,
                 damage_taken,
                 physical_damage_dealt,
                 magic_damage_dealt,
                 most_kill,
                 max_kill,
                 max_death,
                 double_kill,
                 triple_kill,
                 quadra_kill,
                 penta_kill,
                 game_length_second) -> None:
        self._id = id
        self._play = play
        self._win = win
        self._lose = lose
        self._kill = kill
        self._death = death
        self._assist = assist
        self._gold_earned = gold_earned
        self._minion_kill = minion_kill 
        self._turret_kill = turret_kill 
        self._neutral_minion_kill = neutral_minion_kill 
        self._damage_dealt = damage_dealt 
        self._damage_taken = damage_taken 
        self._physical_damage_dealt = physical_damage_dealt 
        self._magic_damage_dealt = magic_damage_dealt 
        self._most_kill = most_kill 
        self._max_kill = max_kill 
        self._max_death = max_death 
        self._double_kill = double_kill 
        self._triple_kill = triple_kill 
        self._quadra_kill = quadra_kill 
        self._penta_kill = penta_kill 
        self._game_length_second = game_length_second
        
    @property
    def id(self) -> int:
        return self._id
    
    @property
    def play(self) -> int:
        return self._play

    @property
    def win(self) -> int:
        return self._win

    @property
    def lose(self) -> int:
        return self._lose

    @property
    def kill(self) -> int:
        return self._kill

    @property
    def death(self) -> int:
        return self._death

    @property
    def assist(self) -> int:
        return self._assist

    @property
    def gold_earned(self) -> int:
        return self._gold_earned

    @property
    def minion_kill(self) -> int:
        return self._minion_kill
 
    @property
    def turret_kill(self) -> int:
        return self._turret_kill

    @property
    def neutral_minion_kill(self) -> int:
        return self._neutral_minion_kill

    @property
    def damage_dealt(self) -> int:
        return self._damage_dealt
        
    @property
    def damage_taken(self) -> int:
        return self._damage_taken
        
    @property
    def physical_damage_dealt(self) -> int:
        return self._physical_damage_dealt
        
    @property
    def magic_damage_dealt(self) -> int:
        return self._magic_damage_dealt

    @property
    def most_kill(self) -> int:
        return self._most_kill
    
    @property
    def max_kill(self) -> int:
        return self._max_kill
    
    @property
    def max_death(self) -> int:
        return self._max_death
    
    @property
    def double_kill(self) -> int:
        return self._double_kill
    
    @property
    def triple_kill(self) -> int:
        return self._triple_kill
    
    @property
    def quadra_kill(self) -> int:
        return self._quadra_kill
    
    @property
    def penta_kill(self) -> int:
        return self._penta_kill
    
    @property
    def game_length_second(self) -> int:
        return self._game_length_second
    
    @property
    def kda(self) -> float:
        return (self._kill + self._assist) / self._death if self._death != 0 else 0

    def __repr__(self) -> str:
        return  f"ChampionStats(ID={self.id}, Win={self.win}, Lose={self.lose}, KDA={round(self.kda, 2)})"