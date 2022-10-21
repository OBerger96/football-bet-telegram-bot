import logging
from datetime import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from bets_handler import Bet, BetsHandler
from matches_handler import MatchesHandler

HELP = "help"
HELP_ARGS_LEN = 0

START = "start"
START_ARGS_LEN = 0

STATUS = "status"
STATUS_ARGS_LEN = 0

BETS = "bets"
BETS_ARGS_LEN = 0

MISSING = "missing"
MISSING_ARGS_LEN = 0

BET = "bet"
BET_MATCH_ID = 0
BET_HOME_SCORE = 1
BET_AWAY_SCORE = 2
BET_ARGS_LEN = 3

BONUS = "bonus"
BONUS_ARGS_LEN = 0
BONUS_USER = 0
BONUS_ADDITION = 1
BONUS_UPDATE_LEN = 2

MATCHES = "matches"
MATCHES_ARGS_LEN = 0

MATCH = "match"
MATCH_ID = 0
MATCH_ARGS_LEN = 1

TABLE = "table"
TABLE_ARGS_LEN = 0
TODAY = "today"
TODAY_ARGS_LEN = 0

REMAINING = "remaining"
REMAINING_ARGS_LEN = 0

USAGES = {
    HELP: f"/{HELP} [command] - Show this help message",
    MATCH: f"/{MATCH} <match-id> - Get all bets and scores of a past match",
    TODAY: f"/{TODAY} - Get the metadata of today matches",
    MATCHES: f"/{MATCHES} - Get the metadata of all of the matches",
    REMAINING: f"/{REMAINING} - Get the metadata of all of remaining matches",
    MISSING: f"/{MISSING} - Get the games that were not bet on yet",
    BET: f"/{BET} <match-id> <home-score> <away-score> - Bet on a match",
    BETS: f"/{BETS} - Get my bets on matches that did not start yet",
    BONUS: f"/{BONUS} Get current bonuses of all bettors",
    STATUS: f"/{STATUS} - Get all current data about me (past bets and scores)",
    TABLE: f"/{TABLE} - Get the rankings table",
}

FULL_USAGE = "Usage:"
for usage_text in USAGES.keys():
    FULL_USAGE += f"\n{USAGES[usage_text]}"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class CommandsHandler:
    def __init__(self):
        self.bets_handler = BetsHandler(BetsHandler.BETS_DB)
        self.matches_handler = MatchesHandler()

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning("An update caused the error '%s'", context.error)

    def usage(self, update, command=None):
        if command in USAGES.keys():
            return f"Usage: {USAGES[command]}"
        else:
            return FULL_USAGE

    def cmd_help(self, update, context):
        if context.args and len(context.args) == 1 and context.args[0] in USAGES.keys():
            update.message.reply_text(self.usage(update, context.args[0]))
            return

        update.message.reply_text(self.usage(update))

    def cmd_start(self, update, context):
        first_name = update.message.chat.first_name if update.message.chat.first_name is not None else ''
        last_name = update.message.chat.last_name if update.message.chat.last_name is not None else ''
        update.message.reply_text(f"Hello, {first_name} {last_name}!")
        update.message.reply_text(self.usage(update))

        if not self.bets_handler.does_bettor_exist(update.message.chat.id):
            self.bets_handler.create_bets_table(update.message.chat.id, ' '.join([first_name, last_name]))

    def cmd_status(self, update, context):
        if len(context.args) != STATUS_ARGS_LEN:
            update.message.reply_text(self.usage(update, STATUS))
            return

        user_bets = self.bets_handler.get_bettor_bets(update.message.chat.id)
        past_bets = [bet for bet in user_bets if self.matches_handler.get_match_by_id(bet.get_match_id()).is_finished()]
        past_bets.sort(key=lambda bet: self.matches_handler.get_match_by_id(bet.get_match_id()).get_datetime())

        total_points = 0

        reply = "Past bets:\n"
        for bet in past_bets:
            past_bet_match = self.matches_handler.get_match_by_id(bet.get_match_id())
            bet_scores = bet.get_scores()
            points_on_bet = past_bet_match.points_on_bet(*bet_scores)
            total_points += points_on_bet
            reply += past_bet_match.format(
                " | ".join([
                    "%id%",
                    f"%home% ({bet_scores[0]}) - %away% ({bet_scores[1]})",
                    "score %home-score%-%away-score%",
                    f"points {points_on_bet}"]))
            reply += '\n'

        bonus_points = self.bets_handler.get_bonus(update.message.chat.id)

        reply += f"\nBonus points: {bonus_points}\n"

        total_points += bonus_points
        reply += f"\nTotal score: {total_points}"

        update.message.reply_text(reply)

    def cmd_bets(self, update, context):
        if len(context.args) != BETS_ARGS_LEN:
            update.message.reply_text(self.usage(update, BETS))
            return

        user_bets = self.bets_handler.get_bettor_bets(update.message.chat.id)
        future_bets = [bet for bet in user_bets if self.matches_handler.get_match_by_id(bet.get_match_id())]
        future_bets.sort(key=lambda bet: self.matches_handler.get_match_by_id(bet.get_match_id()).get_datetime())

        reply = ""
        current_date = None
        for bet in future_bets:
            match = self.matches_handler.get_match_by_id(bet.get_match_id())
            if match.get_datetime().date() != current_date:
                reply += match.format("\n%date%:\n")
                current_date = match.get_datetime().date()
            reply += match.format(f"%id% - %time% - %home% ({bet.get_scores()[0]}) - %away% ({bet.get_scores()[1]})\n")

        if reply:
            update.message.reply_text(reply)
        else:
            update.message.reply_text("No bets found")

    def cmd_missing(self, update, context):
        if len(context.args) != MISSING_ARGS_LEN:
            update.message.reply_text(self.usage(update, MISSING))
            return

        able_to_bet_matches = [match.get_id() for match in self.matches_handler.get_all_matches() if match.is_future()]
        able_to_bet_matches.sort(key=lambda match_id: self.matches_handler.get_match_by_id(match_id).get_datetime())
        user_bets = self.bets_handler.get_bettor_bets(update.message.chat.id)
        user_bets_matches = [bet.get_match_id() for bet in user_bets]
        missing_bets = [match_id for match_id in able_to_bet_matches if match_id not in user_bets_matches]

        missing_text = ""
        for match_id in missing_bets:
            missing_text += self.matches_handler.get_match_by_id(match_id).format("%id% - %date% %time% - %home% vs %away%\n")

        if missing_text:
            update.message.reply_text(f"Missing bets are:\n{missing_text}")
        else:
            update.message.reply_text("All future matches have a bet")

    def cmd_bet(self, update, context):
        if len(context.args) != BET_ARGS_LEN or \
                not self.remove_id_tag(context.args[BET_MATCH_ID]).isdigit() or \
                not context.args[BET_HOME_SCORE].isdigit() or \
                not context.args[BET_AWAY_SCORE].isdigit():
            update.message.reply_text(self.usage(update, BET))
            return

        my_bet = Bet(int(self.remove_id_tag(context.args[BET_MATCH_ID])),
                     int(context.args[BET_HOME_SCORE]),
                     int(context.args[BET_AWAY_SCORE]))

        try:
            past_bet_match = self.matches_handler.get_match_by_id(int(self.remove_id_tag(context.args[BET_MATCH_ID])))
        except Exception:
            update.message.reply_text("No such match")
            return

        if not past_bet_match.is_future():
            update.message.reply_text(past_bet_match.format("Match %id% has already started..."))
            return

        self.bets_handler.place_bet(update.message.chat.id, my_bet)

        update.message.reply_text(past_bet_match.format(f"Placed bet: %home% ({my_bet.get_scores()[0]}) - %away% ({my_bet.get_scores()[1]})"))

    def cmd_bonus(self, update, context):
        if len(context.args) != BONUS_ARGS_LEN and ( \
                        len(context.args) != BONUS_UPDATE_LEN or \
                        not context.args[BONUS_USER].isdigit() or \
                        not self.remove_sign(context.args[BONUS_ADDITION]).isdigit() or \
                        not ('+' in context.args[BONUS_ADDITION] or '-' in context.args[BONUS_ADDITION])):
            update.message.reply_text(self.usage(update, BONUS))
            return

        bettors = self.bets_handler.get_bettors()

        if len(context.args) == BONUS_ARGS_LEN:
            bonuses = {bettors[bonus[BetsHandler.USER_ID]]: bonus[BetsHandler.BONUS] for bonus in self.bets_handler.get_bonuses().items()}

            reply = f"Current bonuses:\n"
            for user in bonuses.keys():
                reply += f"{user} - {bonuses[user]} points\n"

            update.message.reply_text(reply)
            return

        new_bonus = self.bets_handler.add_bonus(int(context.args[BONUS_USER]), int(context.args[BONUS_ADDITION]))
        update.message.reply_text(f"Updated the bonus of {bettors[int(context.args[BONUS_USER])]} to {new_bonus}")

    def cmd_remaining(self, update, context):
        if len(context.args) != MATCHES_ARGS_LEN:
            update.message.reply_text(self.usage(update, MATCHES))
            return

        reply = ""

        future_matches = [match for match in self.matches_handler.get_all_matches() if match.is_future()]
        future_matches.sort(key=lambda match: match.get_datetime())

        current_date = None
        for match in future_matches:
            if match.get_datetime().date() != current_date:
                reply += match.format("\n%date%:\n")
                current_date = match.get_datetime().date()

            reply += match.format("%id% - %time% - %home% vs %away%\n")

        if len(reply.strip()) == 0:
            update.message.reply_text("No future matches")
            return

        update.message.reply_text(reply.strip())

    def cmd_matches(self, update, context):
        if len(context.args) != REMAINING_ARGS_LEN:
            update.message.reply_text(self.usage(update, MATCHES))
            return

        reply = ""

        future_matches = [match for match in self.matches_handler.get_all_matches() if match.is_scheduled()]
        future_matches.sort(key=lambda match: match.get_datetime())

        current_date = None
        for match in future_matches:
            if match.get_datetime().date() != current_date:
                reply += match.format("\n%date%:\n")
                current_date = match.get_datetime().date()

            if match.is_finished():
                reply += match.format("%id% - %time% - %home% (%home-score%) vs (%away-score%) %away%\n")
            else:
                reply += match.format("%id% - %time% - %home% vs %away%\n")

        if len(reply.strip()) == 0:
            update.message.reply_text("No future matches")
            return

        update.message.reply_text(reply.strip())

    def cmd_match(self, update, context):
        if len(context.args) != MATCH_ARGS_LEN or \
                not self.remove_id_tag(context.args[MATCH_ID]).isdigit():
            update.message.reply_text(self.usage(update, MATCH))
            return

        try:
            requested_match = self.matches_handler.get_match_by_id(int(self.remove_id_tag(context.args[MATCH_ID])))
        except Exception:
            update.message.reply_text("No such match")
            return

        if not requested_match.is_started():
            update.message.reply_text(requested_match.format("%date% %time% - %home% vs %away%"))
            return

        reply = requested_match.format("%date% %time% - %home% vs %away% (%home-score% - %away-score%)\n")
        match_bets = self.bets_handler.get_match_bets(int(self.remove_id_tag(context.args[MATCH_ID])))
        bettors = self.bets_handler.get_bettors()

        for bettor in match_bets.keys():
            bettor_bet = match_bets[bettor].get_scores()
            reply += f"{bettors[bettor]}: {bettor_bet[0]}-{bettor_bet[1]} ({requested_match.points_on_bet(*bettor_bet)} points)\n"

        update.message.reply_text(reply)

    def cmd_table(self, update, context):
        if len(context.args) != TABLE_ARGS_LEN:
            update.message.reply_text(self.usage(update, TABLE))
            return

        bettors = self.bets_handler.get_bettors()
        bettors_bonuses = self.bets_handler.get_bonuses()
        bettors_scores = {bettor: 0 for bettor in bettors.keys()}

        for bettor in bettors.keys():
            bets = self.bets_handler.get_bettor_bets(bettor)
            past_bets = [bet for bet in bets if self.matches_handler.get_match_by_id(bet.get_match_id()).is_finished()]

            for bet in past_bets:
                past_bet_match = self.matches_handler.get_match_by_id(bet.get_match_id())
                bettors_scores[bettor] += past_bet_match.points_on_bet(*bet.get_scores())

            if bettor in bettors_bonuses.keys():
                bettors_scores[bettor] += bettors_bonuses[bettor]

        sorted_bettors = [bettor_and_score[0] for bettor_and_score in sorted(bettors_scores.items(), key=lambda item: item[1], reverse=True)]

        reply = ""
        for place_and_bettor in enumerate(sorted_bettors, 1):
            place = place_and_bettor[0]
            bettor = place_and_bettor[1]
            reply += f"#{place} {bettors[bettor]} (with {bettors_scores[bettor]} points)\n"

        update.message.reply_text(reply)

    def remove_id_tag(self, text):
        return text.lstrip('#')

    def remove_sign(self, text):
        if '-' in text:
            return text.replace('-', '', 1)

        return text.replace('+', '', 1)

    def cmd_today(self, update, context):
        if len(context.args) != TODAY_ARGS_LEN:
            update.message.reply_text(self.usage(update, TODAY))
            return

        reply = ""

        future_matches = [match for match in self.matches_handler.get_all_matches()]
        future_matches.sort(key=lambda match: match.get_datetime())

        current_date = datetime.now().date()
        for match in future_matches:
            if match.get_datetime().date() == current_date:
                reply += match.format("\n%date%:\n")
                current_date = match.get_datetime().date()
                reply += match.format("%id% - %time% - %home% vs %away%\n")

        if len(reply.strip()) == 0:
            update.message.reply_text("No matches today")
            return

        update.message.reply_text(reply.strip())


def main():
    # updater = Updater("1804390138:AAF3qeSyYFBcjHyDEGif3UbXAP5fCTCSzUw", use_context=True)  # TESTER
    updater = Updater("5469557083:AAGqa0y7ZubAtlQyi2IULHOUmWzmGYqulK8", use_context=True)  # PRODUCTION
    dispatcher = updater.dispatcher
    commands_handler = CommandsHandler()

    dispatcher.add_error_handler(commands_handler.error)

    dispatcher.add_handler(CommandHandler(HELP, commands_handler.cmd_help))
    dispatcher.add_handler(CommandHandler(START, commands_handler.cmd_start))

    dispatcher.add_handler(CommandHandler(STATUS, commands_handler.cmd_status))
    dispatcher.add_handler(CommandHandler(BETS, commands_handler.cmd_bets))
    dispatcher.add_handler(CommandHandler(MISSING, commands_handler.cmd_missing))
    dispatcher.add_handler(CommandHandler(BET, commands_handler.cmd_bet))
    dispatcher.add_handler(CommandHandler(BONUS, commands_handler.cmd_bonus))
    dispatcher.add_handler(CommandHandler(MATCHES, commands_handler.cmd_matches))
    dispatcher.add_handler(CommandHandler(REMAINING, commands_handler.cmd_remaining))
    dispatcher.add_handler(CommandHandler(MATCH, commands_handler.cmd_match))
    dispatcher.add_handler(CommandHandler(TABLE, commands_handler.cmd_table))
    dispatcher.add_handler(CommandHandler(TODAY, commands_handler.cmd_today))

    dispatcher.add_handler(MessageHandler(Filters.text, commands_handler.cmd_help))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
