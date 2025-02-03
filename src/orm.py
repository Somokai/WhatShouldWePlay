from pony.orm import (
    Database,
    PrimaryKey,
    Set,
    Required,
    Optional,
    MultipleObjectsFoundError,
    composite_key,
    db_session,
    select,
)

db = Database()
_is_initialized = False  # Track initialization state


class Game(db.Entity):
    key = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    player_count = Optional(int)
    steam_metadata = Optional("SteamMetaData")
    players = Set("Player", reverse="games")
    banners = Set("Player", reverse="banned")
    composite_key(name, steam_metadata)

    @db_session
    def set_player_count(self, count: int):
        self.player_count = count

    @db_session
    def get_player_count(self) -> list["Player"]:
        return self.player_count


class Player(db.Entity):
    key = PrimaryKey(int, auto=True)
    id = Required(str, unique=True)
    name = Required(str)
    games = Set("Game", reverse="players")
    banned = Set("Game", reverse="banners")

    @db_session
    def add_games(self, *names: str):
        for name in names:
            try:
                steam_metadata = SteamMetaData.get(name=name)
            except MultipleObjectsFoundError:
                steam_metadata = None  # Set to none for now, because we don't have appid
            game = Game.get(name=name) or Game(name=name, steam_metadata=steam_metadata)
            self.games += game

    def add_games_with_appid(self, *appids: int):
        for appid in appids:
            steam_metadata = SteamMetaData.get(appid=appid)
            game = Game.get(steam_metadata=steam_metadata)
            if not game:
                game = Game.get(name=steam_metadata.name)
                if not game:
                    game = Game(name=steam_metadata.name, steam_metadata=steam_metadata)
                else:
                    game.steam_metadata = steam_metadata
            self.games += game

    @db_session
    def add_banned_games(self, *names: str):
        for name in names:
            game = Game.get(name=name) or Game(name=name)
            self.banned += game

    @db_session
    def remove_games(self, *names: str):
        for name in names:
            game = Game.get(name=name)
            if game:
                self.games.remove(game)

    @db_session
    def remove_banned_games(self, *names: str):
        for name in names:
            game = Game.get(name=name)
            if game:
                self.banned.remove(game)

    @db_session
    def get_games(self) -> list["Game"]:
        return list(self.games)

    @db_session
    def get_banned_games(self) -> list["Game"]:
        return list(self.banned)


class SteamMetaData(db.Entity):
    key = PrimaryKey(int, auto=True)
    appid = Required(int, unique=True)
    name = Required(str)  # Games can have the same name, but not the same appid
    game = Optional(Game)

    @db_session
    def add_games(games: list[dict[str, str]]):
        appids_set_cur = set(select(g.appid for g in SteamMetaData)[:])
        appids_set_new = set(g["appid"] for g in games)
        games_to_add = appids_set_new - appids_set_cur

        # Extract the games to add from the original games list
        games_to_add_details = [game for game in games if game["appid"] in games_to_add]

        for game in games_to_add_details:
            if not game["name"]:
                continue
            # The appid is unique, but there are dupes in the api response
            if not SteamMetaData.get(appid=game["appid"]):
                SteamMetaData(appid=game["appid"], name=game["name"])
        return


def init_database(db_path: str = ":memory:"):
    global _is_initialized
    if _is_initialized:
        return
    _is_initialized = True
    db.bind(provider="sqlite", filename=db_path, create_db=True)
    db.generate_mapping(create_tables=True)
