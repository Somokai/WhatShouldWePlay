from pony.orm import Database, PrimaryKey, Set, Required, Optional, db_session
db = Database()

class Game(db.Entity):
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
    # message.author.id
    key = PrimaryKey(int, auto=True)
    id = Required(str, unique=True)
    # message.author.name
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


def init_database(db_path: str = ":memory:"):
    db.bind(provider="sqlite", filename=db_path, create_db=True)
    db.generate_mapping(create_tables=True)
