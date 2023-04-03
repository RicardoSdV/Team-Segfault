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

        who = (1, 2, 3, 4, 5) # Tank ids of who is to move
        where = (0, 0, 0)# Where are they to move, coords
        new_positions: dict = self._game_map.move_to(who, where)
        moves = [{'vehicle_id': k, 'target': {'x': v[0], 'y': v[1], 'z': v[2]}} for k, v in new_positions.items()]

        return moves, shots


