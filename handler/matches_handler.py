import datetime
import json
from datetime import timedelta
from typing import List

import requests
from dateutil import parser as dateParser
from numpy import sign

import secrets


def get_current_time():
    return datetime.datetime.now(datetime.timezone.utc) + timedelta(hours=3)


class Match:
    match_id: int
    match_day: int
    date_time: str
    home_team: str
    away_team: str
    score_home_team: int
    score_away_team: int

    def __init__(self, match_id: int,
                 match_day: int,
                 date_time: datetime.datetime,
                 home_team: str,
                 away_team: str,
                 score_home_team: int,
                 score_away_team: int):
        self.match_id = match_id - 391881 + 1
        self.match_day = match_day
        self.date_time = date_time
        self.home_team = home_team
        self.away_team = away_team
        self.score_home_team = score_home_team
        self.score_away_team = score_away_team

    @staticmethod
    def from_web_json(json_match):
        return Match(match_id=json_match['id'],
                     match_day=json_match['matchday'],
                     date_time=Match._set_datetime_in_israel(json_match['utcDate']),
                     home_team=json_match['homeTeam']['name'],
                     away_team=json_match['awayTeam']['name'],
                     score_home_team=Match._get_score_home(json_match=json_match),
                     score_away_team=Match._get_score_away(json_match=json_match))

    @staticmethod
    def _get_score_home(json_match):
        full_time_score = json_match['score']['fullTime']['homeTeam']
        extra_time_score = json_match['score']['extraTime']['homeTeam']
        penalty_shootout = json_match['score']['penalties']['homeTeam']
        if extra_time_score:
            full_time_score = full_time_score - extra_time_score
        if penalty_shootout:
            full_time_score = full_time_score - penalty_shootout
        return full_time_score

    @staticmethod
    def _get_score_away(json_match):
        full_time_score = json_match['score']['fullTime']['awayTeam']
        extra_time_score = json_match['score']['extraTime']['awayTeam']
        penalty_shootout = json_match['score']['penalties']['awayTeam']
        if extra_time_score:
            full_time_score = full_time_score - extra_time_score
        if penalty_shootout:
            full_time_score = full_time_score - penalty_shootout
        return full_time_score

    @staticmethod
    def _set_datetime_in_israel(datetime: str):
        return dateParser.parse(datetime) + timedelta(hours=2)

    def get_datetime(self):
        return self.date_time

    def get_id(self):
        return self.match_id

    def is_scheduled(self) -> bool:
        return self.match_day is not None and \
               self.date_time is not None and \
               self.home_team is not None and \
               self.away_team is not None

    def is_finished(self) -> bool:
        return self.score_home_team is not None and \
               self.score_away_team is not None

    def is_started(self) -> bool:
        return get_current_time() >= self.date_time

    def is_future(self) -> bool:
        return self.is_scheduled() and not self.is_started()

    def format(self, format_pattern: str) -> str:
        return format_pattern \
            .replace('%date%', self.date_time.strftime("%d/%m/%Y")) \
            .replace('%time%', self.date_time.strftime("%H:%M")) \
            .replace('%home%', self.home_team) \
            .replace('%away%', self.away_team) \
            .replace('%home-score%', str(self.score_home_team)) \
            .replace('%away-score%', str(self.score_away_team)) \
            .replace('%id%', f"#{self.match_id}")

    def points_on_bet(self, home_bet, away_bet):
        if not self.is_finished():
            return 0

        points = 0
        if home_bet == self.score_home_team:
            points += 1
        if away_bet == self.score_away_team:
            points += 1
        if home_bet - away_bet == self.score_home_team - self.score_away_team:
            points += 2
        if sign(home_bet - away_bet) == sign(self.score_home_team - self.score_away_team):
            points += 2

        return points

    def __iter__(self):
        yield self.match_id
        yield self.match_day
        yield self.date_time
        yield self.home_team
        yield self.away_team
        yield self.score_home_team
        yield self.score_away_team

    def __str__(self):
        match_id = f"#{self.match_id}: "
        date_and_teams = f"{self.date_time} - {self.home_team} vs {self.away_team}"
        scores = f" ({self.score_home_team} - {self.score_away_team})" \
            if (self.score_home_team is not None and self.score_away_team is not None) \
            else ""

        return match_id + date_and_teams + scores


class MatchesHandler:

    def __init__(self):
        self.reload_all_matches()

    def reload_all_matches(self):
        request = requests.get(url='https://api.football-data.org/v2/competitions/WC/matches', headers={'X-Auth-Token': 'a5b3683eec044716a6c0730cb9c56917'})
        response_matches = json.loads(request.content)['matches']
        matches_list = [Match.from_web_json(match_json) for match_json in response_matches]
        self.matches = {match.get_id(): match for match in matches_list}
        self.next_reload_time = self.get_next_reload_time()

    @staticmethod
    def get_next_reload_time():
        current_time = get_current_time().time()
        is_between_00_00_to_01_00 = datetime.time(1, 0) >= current_time >= datetime.time(0, 0)
        is_between_16_00_to_23_59 = datetime.time(23, 59) >= current_time >= datetime.time(16, 0)

        if is_between_00_00_to_01_00 or is_between_16_00_to_23_59:
            return get_current_time() + timedelta(minutes=10)
        return get_current_time() + timedelta(hours=1)

    def reload_if_needed(self):
        if self.next_reload_time <= get_current_time():
            self.reload_all_matches()

    def get_match_by_id(self, match_id: int) -> Match:
        self.reload_if_needed()
        return self.matches[match_id]

    def get_all_matches(self) -> List[Match]:
        self.reload_if_needed()
        return self.matches.values()


if __name__ == "__main__":
    print('----------------- Testing initialization ---------------------------')
    handler = MatchesHandler()

    print('----------------- Testing get match by id ---------------------------')

    matches_ids = [match.match_id for match in handler.get_all_matches()]
    matches_ids.sort()
    print(matches_ids)

    print(handler.get_match_by_id(1))

    print('----------------- Testing get all matches ---------------------------')
    matches = handler.get_all_matches()
    for match in matches:
        print(match)

    print('----------------- Testing Match format ---------------------------')
    match = handler.get_match_by_id(1)
    print(match.format("%date% %time%"))
    print(match.format("%time% %date%"))
    print(match.format("%time% %date%"))
    print(match.format("%time%-%date%"))
    print(match.format("%time% - %date% - %home% vs %away%"))
    print(match.format("date: %date%"))
