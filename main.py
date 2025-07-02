import json
import random
import re
from datetime import datetime
from enum import Enum

import pyttsx3
import speech_recognition as sr

from extractor import NumberExtractor


class Recognizer(Enum):
    GOOGLE = 1
    VOSK = 2
    BOTH = 3


class Talker:
    def __init__(self):
        self._speaker = pyttsx3.init()
        self._speaker.setProperty("rate", 220)
        self._recognizer = sr.Recognizer()
        self._mic = sr.Microphone()
        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source)

    def _vosk_recognizer(self, audio) -> str:
        return json.loads(self._recognizer.recognize_vosk(audio, language="ru"))["text"].lower()

    def _google_recognizer(self, audio) -> str:
        text = ""
        try:
            text = self._recognizer.recognize_google(audio, language="ru")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return text.lower()

    def listen(self, recognizer: Recognizer = Recognizer.BOTH) -> str:
        print("start to listen")
        with self._mic as source:
            audio = self._recognizer.listen(source)
            match recognizer:
                case recognizer.VOSK:
                    text = self._vosk_recognizer(audio)
                case recognizer.GOOGLE:
                    text = self._google_recognizer(audio)
                case recognizer.BOTH:
                    text = self._google_recognizer(audio) or self._vosk_recognizer(audio)
        print(f"speech recognized: {text}")
        return text

    def speak(self, text: str):
        print("start speaking")
        self._speaker.say(text)
        self._speaker.runAndWait()
        print("stop speaking")


class Game501:
    def __init__(self):
        self.talker = Talker()
        self.players = self._get_players()
        self.scores = {player: 101 for player in self.players}
        self.current_player = random.choice(self.players)
        self.current_turn = []
        self.turns = []
        self.game_is_up = False

    def _get_players(self) -> tuple[str]:
        self.talker.speak("Давайте начнем новую игру")
        players = []
        for i in range(2):
            while True:
                self.talker.speak(f"Назовите имя игрока {i + 1}")
                player_name = self.talker.listen().capitalize()
                self.talker.speak(f"Игрока {i + 1} зовут {player_name}, все верно?")
                answer = self.talker.listen().lower()
                if "нет" in answer:
                    continue
                players.append(player_name)
                break
        self.talker.speak("Игроки сохранены")
        return tuple(players)

    @staticmethod
    def _get_number_from_text(text: str | None) -> int | None:
        extractor = NumberExtractor()
        text = extractor.replace_groups(text)
        if not text:
            return None

        result = re.findall(r"\d+", text)
        if len(result) != 1:
            return None

        return int(result[0])

    def _announce_player(self):
        self.talker.speak(f"Бросает {self.current_player}")

    def _switch_player(self):
        next_player = next(iter(set(self.players) - {self.current_player}))
        self.turns.append((self.current_player, self.current_turn))
        self.current_turn = []
        self.current_player = next_player
        self._announce_player()
        self.talker.speak(f"Осталось набрать {self.scores[self.current_player]} очков")

    def _make_throw(self):
        print(self.scores)
        throw_text = self.talker.listen()
        if any(miss_word in throw_text for miss_word in ("мимо", "промах", "молоко")):
            throw_value = 0
        else:
            throw_value = self._get_number_from_text(throw_text)
        if throw_value is None:
            self.talker.speak("Повторите результат броска")
            return

        if throw_value > 180:
            self.talker.speak("Ну ты и фантазер, а теперь скажи честно")
            return

        player_score = self.scores[self.current_player]
        player_score -= throw_value
        if player_score < 0:
            self.scores[self.current_player] += sum(self.current_turn)
            self.talker.speak("Перебор")
            self._switch_player()
            return

        self.scores[self.current_player] = player_score
        self.current_turn.append(throw_value)
        print(f"current turn: {self.current_turn}")
        if player_score == 0:
            self.turns.append((self.current_player, self.current_turn))
            self.game_is_up = False
            return

        if len(self.current_turn) == 3:
            self._switch_player()

    def _run_main_loop(self):
        self._announce_player()
        while self.game_is_up:
            self._make_throw()

    def _dump_game(self):
        with open("history.json", encoding="utf-8") as file:
            try:
                history_data = json.load(file)
            except json.JSONDecodeError:
                history_data = {}
        history_data[datetime.now().isoformat()] = self.turns
        with open("history.json", "w", encoding="utf-8") as file:
            json.dump(history_data, file, ensure_ascii=False)

    def start_game(self):
        self.talker.speak("Начинаем игру")
        self.game_is_up = True
        self._run_main_loop()
        self.talker.speak(f"Победил игрок по имени {self.current_player}")
        self._dump_game()


def main():
    game = Game501()
    game.start_game()


if __name__ == "__main__":
    main()
