from abc import ABC

from src.client.server_enum import Action
from src.entity.tank import Tank
from src.player.player import Player
from typing import List


class BotPlayer(Player, ABC):
    def __init__(self, name: str, password: str = None, is_observer: bool = None):
        super().__init__(name, password, is_observer)

    def play_moves(self) -> (List, List):
        moves = []; shots = []

        next_bests = self._game_map.next_best_hexs()
        for i in range(len(next_bests)):
            next_best = next_bests[i]
            moves.append({'vehicle_id': i+1, 'target': {'x': next_best[0], 'y': next_best[1], 'z': next_best[2]}})

        return moves, shots


