from rlbot.agents.base_script import BaseScript
from queue import Queue
import threading
import time
import requests
from typing import List
import json


class RLBotTwitchScript(BaseScript):
    def __init__(self, broadcaster_id):
        super().__init__("RLBotTwitchScript")
        self.broadcaster_id = broadcaster_id
        with open("client_data.txt", "r") as f:
            self.client_id, self.client_secret = [line.strip().split("=")[1] for line in f.readlines()]

    def betting(self, condition, channel_name: str, prediction_title: str, prediction_outcomes,
                prediction_window: int = 120):
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
        # get starting scores
        starting_scores = self._get_scores()

        # wait until condition(Blue was first to score 5 goals) is met (rlbot)

        # end bet (twitch api)
        headers = {
            'Authorization': 'Bearer cfabdegwdoklmawdzdo98xt2fo512y',
            'Client-Id': self.client_id,
        }

        json_data = {
            'broadcaster_id': '141981764',
            'id': prediction_id,
            'status': 'RESOLVED',
            'winning_outcome_id': '73085848-a94d-4040-9d21-2cb7a89374b7',
        }

        response = requests.patch('https://api.twitch.tv/helix/predictions', headers=headers, json=json_data)
        if response.status_code == 200:
            print("Ended prediction successfully")
        else:
            print("Failed to end prediction!")
        pass

    def _get_scores(self):
        scores = [team.score for team in self.game_tick_packet.teams]
        return scores

    def run(self):
        while True:
            self.packet = self.wait_game_tick_packet()
            self.ball_predictions = self.get_ball_prediction_struct()
            if not self.f_packet:
                self.f_packet = self.get_field_info()
            if self.packet.game_info.is_match_ended:
                print("Game is over, exiting caster script.")
                self.gameWrapUp()
                break

            if self.firstIter:
                if self.packet.num_cars >= 1:
                    if self.joinTimer <= 0:
                        self.joinTimer = time.time()
                    # arbitrary timer to ensure all cars connected
                    if time.time() - self.joinTimer >= 1:
                        self.firstIter = False
                        self.currentTime = float(self.packet.game_info.seconds_elapsed)
                        self.gatherMatchData()
                        self.zoneInfo = ZoneAnalyst(self.currentZone, self.currentTime)
                        self.KOE = KickoffExaminer(self.currentTime)

            self.timeCheck(float(self.packet.game_info.seconds_elapsed))
            self.match_clock_handler()
            if not self.firstIter:

                self.updateGameBall()
                self.updateTouches()
                self.demo_check()
                self.updateTeamsInfo()
                self.handleShotDetection()
                self.scoreCheck()
                self.overtimeCheck()
                self.kickOffAnalyzer()
                self.mid_game_summary()
                if self.packet.game_info.is_kickoff_pause:
                    self.zoneInfo.zoneTimer = self.currentTime
                if self.currentTime - self.lastCommentTime >= 8:
                    self.randomComment()


if __name__ == "__main__":
    BROADCASTER_ID = "141981764"
    script = RLBotTwitchScript(BROADCASTER_ID)
    script.run()
