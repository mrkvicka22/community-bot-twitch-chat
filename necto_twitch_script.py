from rlbot.agents.base_script import BaseScript
from twitchAPI.pubsub import PubSub
from twitchAPI.twitch import Twitch, PredictionStatus
from twitchAPI.types import AuthScope
from twitchAPI.oauth import UserAuthenticator
from uuid import UUID


class RLBotTwitchScript(BaseScript):
    def __init__(self):
        super().__init__("RLBotTwitchScript")

        # keys and secrets and stuff
        with open("client_data.txt", "r") as f:
            self.CLIENT_ID, self.CLIENT_SECRET, self.USER = [line.strip().split("=")[1] for line in
                                                             f.readlines()]
        # twitch api innit
        self.twitch = Twitch(self.CLIENT_ID, self.CLIENT_SECRET)
        self.target_scope = [AuthScope.CHANNEL_READ_REDEMPTIONS,
                             AuthScope.CHANNEL_MANAGE_POLLS,
                             AuthScope.CHANNEL_MANAGE_PREDICTIONS,
                             AuthScope.CHANNEL_READ_POLLS]
        self.auth = UserAuthenticator(self.twitch, self.target_scope, force_verify=False)
        self.token, self.refresh_token = self.auth.authenticate()
        self.twitch.authenticate_app(self.target_scope)
        self.twitch.set_user_authentication(self.token, self.target_scope, self.refresh_token)
        self.user_id = self.twitch.get_users(logins=[self.USER])['data'][0]['id']

        # starting listening to public events
        self.pubsub = PubSub(self.twitch)

        # rlbot innit
        self.packet = self.wait_game_tick_packet()
        self.f_packet = self.get_field_info()

        # betting
        self.n_goals = 50

    def goals_check_condition(self, starting_score):
        current_scores = self._get_scores()
        if starting_score[0] + 5 <= current_scores[0]:  # might break cos pizza
            # blue wins the prediction
            return 0
        elif starting_score[1] + 5 <= current_scores[1]:
            # orange wins the prediction
            return 1
        else:
            return None

    def _get_scores(self):
        scores = [team.score for team in self.packet.teams]
        return scores

    def _handle_channel_points(self, uuid: UUID, data: dict):
        raise NotImplementedError

    def _handle_end_prediction(self, prediction_id, outcomes, result):
        winning_outcome_id = outcomes[result]["id"]
        self.twitch.end_prediction(self.user_id, prediction_id, PredictionStatus.RESOLVED, winning_outcome_id)

    def _handle_create_prediction(self):
        response = self.twitch.create_prediction(self.user_id, f"Who is going to score {self.n_goals} goals first",
                                                 ["Blue", "Orange"], 120)
        return response["data"]["outcomes"]

    def run(self):
        prediction_active = False
        prediction_id = None
        outcomes = None
        self.pubsub.start()
        self.pubsub.listen_channel_points(self.user_id, callback_func=self._handle_channel_points)
        starting_score = self._get_scores()
        while True:
            self.packet = self.wait_game_tick_packet()
            if not self.f_packet:
                self.f_packet = self.get_field_info()
            if self.packet.game_info.is_match_ended:
                break

            # handle predictions
            if prediction_active:
                result = self.goals_check_condition(starting_score)
                if result is not None:
                    self._handle_end_prediction(prediction_id, outcomes, result)
            else:
                starting_score = self._get_scores()
                outcomes = self._handle_create_prediction()


if __name__ == "__main__":
    script = RLBotTwitchScript()
    script.run()
