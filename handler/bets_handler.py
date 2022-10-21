import sqlite3

import secrets


class Bet:
    match_id: int
    home_score: int
    away_score: int

    def __init__(self, match_id: int,
                 home_score: int,
                 away_score: int):
        self.match_id = match_id
        self.home_score = home_score
        self.away_score = away_score

    def __iter__(self):
        yield self.match_id
        yield self.home_score
        yield self.away_score

    def __repr__(self):
        return f"Bet(match_id={self.match_id}, home_score={self.home_score}, away_score={self.away_score})"

    def _get_match_id(self):
        return self.match_id

    def _get_scores(self):
        return [self.home_score, self.away_score]


class BetsHandler:
    _TABLE_NAME_FORMAT = "bets_of_{}"

    CREATE_USERS_QUERY = """
        CREATE TABLE users(
        bettor_id INTEGER NOT NULL PRIMARY KEY,
        bettor_name TEXT NOT NULL);
    """

    INSERT_TABLE_USER_QUERY = """
        REPLACE INTO users
        (bettor_id, bettor_name)
        VALUES (?,?);
    """

    SELECT_ALL_USERS_QUERY = """
        SELECT *
        FROM users;
    """

    CREATE_BETS_TABLE_QUERY = f"""
        CREATE TABLE {_TABLE_NAME_FORMAT}(
        match_id INTEGER NOT NULL PRIMARY KEY,
        home_score INTEGER NOT NULL,
        away_score INTEGER NOT NULL);
    """

    INSERT_BET_QUERY = f"""
        REPLACE INTO {_TABLE_NAME_FORMAT}
        (match_id, home_score, away_score) 
        VALUES (?,?,?);
    """

    SELECT_BET_QUERY = f"""
        SELECT * 
        FROM {_TABLE_NAME_FORMAT} 
        WHERE match_id=?;
    """

    SELECT_ALL_BETS_QUERY = f"""
        SELECT * 
        FROM {_TABLE_NAME_FORMAT};
    """

    CREATE_BONUSES_TABLE_QUERY = """
        CREATE TABLE bonuses(
        bettor_id INTEGER NOT NULL PRIMARY KEY,
        bonus INTEGER NOT NULL);
    """

    SELECT_BONUS_QUERY = f"""
        SELECT * 
        FROM bonuses
        WHERE bettor_id=?;
    """

    SELECT_BONUSES_QUERY = f"""
        SELECT * 
        FROM bonuses;
    """

    UPDATE_BONUS_QUERY = f"""
        REPLACE INTO bonuses
        (bettor_id, bonus) 
        VALUES (?,?);
    """

    USER_ID = 0
    USER_NAME = 1
    BONUS = 1

    connection: sqlite3.Connection

    def __init__(self, db_name):
        self.db_name = db_name

        with self._create_connection(self.db_name) as connection:
            try:
                connection.execute(BetsHandler.CREATE_USERS_QUERY)
            except:
                pass

        with self._create_connection(self.db_name) as connection:
            try:
                connection.execute(BetsHandler.CREATE_BONUSES_TABLE_QUERY)
            except:
                pass

    @staticmethod
    def _create_connection(db_name):
        return sqlite3.connect(db_name)

    def create_bets_table(self, bettor_id, bettor_name):
        with self._create_connection(self.db_name) as connection:
            try:
                connection.execute(BetsHandler.CREATE_BETS_TABLE_QUERY.format(bettor_id))
            except:
                pass

            connection.execute(BetsHandler.INSERT_TABLE_USER_QUERY, (bettor_id, bettor_name))
            connection.execute(BetsHandler.UPDATE_BONUS_QUERY, (bettor_id, 0))
            connection.commit()

    def get_bettors(self):
        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()
            cursor.execute(BetsHandler.SELECT_ALL_USERS_QUERY)
            users = cursor.fetchall()

        return {user[BetsHandler.USER_ID]: user[BetsHandler.USER_NAME] for user in users}

    def does_bettor_exist(self, bettor_id):
        return bettor_id in self.get_bettors().keys()

    def place_bet(self, bettor_id, bet):
        with self._create_connection(self.db_name) as connection:
            connection.execute(BetsHandler.INSERT_BET_QUERY.format(bettor_id), (bet.match_id, bet.home_score, bet.away_score))
            connection.commit()

    def get_bet(self, bettor_id, match_id):
        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()
            cursor.execute(BetsHandler.SELECT_BET_QUERY.format(bettor_id), (match_id,))
            bet_values = cursor.fetchall()[0]

        return Bet(*bet_values)

    def get_bettor_bets(self, bettor_id):
        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()
            cursor.execute(BetsHandler.SELECT_ALL_BETS_QUERY.format(bettor_id))
            all_bets = cursor.fetchall()

        return [Bet(*data) for data in all_bets]

    def get_match_bets(self, match_id):
        match_bets = {}

        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()

            cursor.execute(BetsHandler.SELECT_ALL_USERS_QUERY)
            users = cursor.fetchall()

            for user in users:
                cursor.execute(BetsHandler.SELECT_BET_QUERY.format(user[BetsHandler.USER_ID]), (match_id,))
                result = cursor.fetchall()
                if len(result) > 0:
                    match_bets[user[BetsHandler.USER_ID]] = Bet(*(result[0]))

        return match_bets

    def get_bonus(self, bettor_id):
        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()
            cursor.execute(BetsHandler.SELECT_BONUS_QUERY, (bettor_id,))
            return cursor.fetchall()[0][BetsHandler.BONUS]

    def get_bonuses(self):
        with self._create_connection(self.db_name) as connection:
            cursor = connection.cursor()
            cursor.execute(BetsHandler.SELECT_BONUSES_QUERY)
            bonuses = cursor.fetchall()

            return {bonus[BetsHandler.USER_ID]: bonus[BetsHandler.BONUS] for bonus in bonuses}

    def add_bonus(self, bettor_id, added_bonus):
        with self._create_connection(self.db_name) as connection:
            connection.execute(BetsHandler.UPDATE_BONUS_QUERY, (bettor_id, self.get_bonus(bettor_id) + added_bonus))
            connection.commit()

        return self.get_bonus(bettor_id)


if __name__ == "__main__":
    print('----------------- Testing DB handler ---------------------------')
    bets_handler = BetsHandler(secrets.BETS_TESTS_DB)
    print("Successfully Connected to SQLite")

    bets_handler.create_bets_table(123, 'Simba')
    bets_handler.place_bet(123, Bet(111, 2, 1))
    bets_handler.place_bet(123, Bet(111, 1, 1))
    bets_handler.place_bet(123, Bet(115, 1, 3))

    print("Database loaded - the saved data is:")
    print(bets_handler.get_bet(123, 111))
    print(bets_handler.get_bet(123, 115))

    print(bets_handler.get_bettor_bets(123))
