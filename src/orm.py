from pony.orm import (
    Database,
    PrimaryKey,
    Set,
    Required,
    Optional,
    db_session,
    select,
)

db = Database()
_is_initialized = False  # Track initialization state


class GameTable(db.Entity):
    appid = PrimaryKey(int, auto=True)
    name = Optional(str)  # Games can have the same name, but not the same appid

    @db_session
    def add_games(games: list[dict[str, str]]):
        appids_set_cur = set(select(g.appid for g in GameTable)[:])
        appids_set_new = set(g["appid"] for g in games)
        games_to_add = appids_set_new - appids_set_cur

        # Extract the games to add from the original games list
        games_to_add_details = [game for game in games if game["appid"] in games_to_add]

        for game in games_to_add_details:
            GameTable(appid=game["appid"], name=game["name"])
        return


class Game(db.Entity):
    key = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    player_count = Optional(int)
    players = Set("Player", reverse="games")
    banners = Set("Player", reverse="banned")

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
            game = Game.get(name=name) or Game(name=name)
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


def init_database(db_path: str = ":memory:", applist: str = None):
    global _is_initialized
    if _is_initialized:
        return
    _is_initialized = True
    db.bind(provider="sqlite", filename=db_path, create_db=True)
    db.generate_mapping(create_tables=True)

    with db_session:
        if applist:
            GameTable.add_games(applist)
