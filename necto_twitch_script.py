from rlbot.agents.base_script import BaseScript
import requests
import json
import asyncio


class RLBotTwitchScript(BaseScript):
    def __init__(self, broadcaster_id):
        super().__init__("RLBotTwitchScript")
        self.broadcaster_id = broadcaster_id
        # keys and secrets and stuff
        with open("client_data.txt", "r") as f:
            self.client_id, self.client_secret, self.user, self.oauth = [line.strip().split("=")[1] for line in
                                                                         f.readlines()]
        # rlbot innit
        self.packet = self.wait_game_tick_packet()
        self.f_packet = self.get_field_info()

    def _start_prediction(self, channel_name: str, prediction_title: str, prediction_outcomes,
                          prediction_window: int):
        # create a bet (twitch api)
        headers = {
            "Authorization": " ",
            "Client-ID": self.client_id,
            'Content-Type': 'application/json',
        }
        data = {"broadcaster_id": self.broadcaster_id,
                "title": prediction_title,
                "outcomes": prediction_outcomes,
                "prediction_window": prediction_window
                }
        response = requests.post(f"https://api.twitch.tv/{channel_name}/predictions", data=data, headers=headers)
        if response.status_code == 200:
            print("Created prediction successfully")
        else:
            print("Failed to start prediction!")
        response_json = json.load(response.json())
        prediction_id = response_json["data"]["id"]
        blue_outcome_id, pink_outcome_id = [outcome["id"] for outcome in response_json["data"]["outcomes"]]
        return prediction_id, blue_outcome_id, pink_outcome_id

    def _end_prediction(self, prediction_id, result_id):
        # end bet (twitch api)
        headers = {
            'Authorization': 'Bearer cfabdegwdoklmawdzdo98xt2fo512y',
            'Client-Id': self.client_id,
        }

        json_data = {
            'broadcaster_id': self.broadcaster_id,
            'id': prediction_id,
            'status': 'RESOLVED',
            'winning_outcome_id': result_id,
        }

        response = requests.patch('https://api.twitch.tv/helix/predictions', headers=headers, json=json_data)
        if response.status_code == 200:
            print("Ended prediction successfully")
        else:
            print("Failed to end prediction!")

    async def goals_check_condition(self, starting_score):
        # wait until condition(Blue was first to score 5 goals) is met (rlbot)
        while True:
            current_scores = self._get_scores()
            if starting_score[0] + 5 <= current_scores[0]:  # might break cos pizza
                # blue wins the prediction
                return 0
            elif starting_score[1] + 5 <= current_scores[1]:
                # orange wins the prediction
                return 1
            else:
                print("No-one won yet")
            await asyncio.sleep(1)

    def betting(self, channel_name, prediction_title, prediction_outcomes, prediction_window: int = 120):
        starting_scores = self._get_scores()

        t = self._start_prediction(channel_name, prediction_title, prediction_outcomes, prediction_window)
        prediction_id, blue_outcome_id, pink_outcome_id = t
        result = await self.goals_check_condition(starting_scores)

        if result:
            result_id = pink_outcome_id
        else:
            result_id = blue_outcome_id

        self._end_prediction(prediction_id, result_id)
        print("it worked?")

    def _get_scores(self):
        scores = [team.score for team in self.packet.teams]
        return scores

    def run(self):
        while True:
            self.packet = self.wait_game_tick_packet()
            if not self.f_packet:
                self.f_packet = self.get_field_info()
            if self.packet.game_info.is_match_ended:
                break


if __name__ == "__main__":
    BROADCASTER_ID = "141981764"
    script = RLBotTwitchScript(BROADCASTER_ID)
    script.run()
