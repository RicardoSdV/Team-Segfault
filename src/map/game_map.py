import itertools
from collections import defaultdict
import random as rnd
from typing import List, Dict
import matplotlib.pyplot as plt
from src.client.server_enum import Action
from src.entity.entity import Entity
from src.entity.tank import Tank
from src.map.hex import Hex

class GameMap:
    __THIRD = 1/3
    def __init__(self, game_map: dict):
        self.__map_size: int = 0
        self.__entities: dict[Hex, Entity] = {}
        # tank_id -> hex
        self.__tank_positions: dict[int, Hex] = {}
        self.__tanks: dict[int, Tank] = {}
        # tanks_in_base could probably be deleted
        self.__tanks_in_base: list[int] = []
        self.__base: [Hex] = []
        self.parse_map(game_map)

       # self.used_hexs_by_turn = [] #[thisTurn -> [(x,y,z), (x,y,z), ...],
                                # [],[]]

    def parse_map(self, game_map: dict) -> None:
        """
        Saves entity data
        :param game_map: dict of GAME_MAP response
        :return: None
        """
        self.__map_size = game_map["size"]
        for entity, coordinates in game_map["content"].items():
            for coordinate in coordinates:
                h = Hex([coordinate["x"], coordinate["y"], coordinate["z"]])
                if entity == "base":
                    self.__base.append(h)
                else:
                    self.__entities[h] = Entity(entity)

    def update(self, game_state: dict) -> None:
        """
         Updates the map information based on passed dictionary
        :param game_state: either a GAME_STATE dict or GAME_ACTIONS dict
        :return: None
        """
        if "actions" in game_state:
            for action in game_state["actions"]:
                data = action["data"]
                tank_id = data["vehicle_id"]
                new_position = Hex([data['target']['x'], data['target']['y'], data['target']['z']])

                tank = self.__tanks[tank_id]
                if action["action_type"] == Action.MOVE:
                    # if tank was in base before movement, remove it from tanks_in_base
                    if self.__tank_positions[tank_id] in self.__base:
                        self.__tanks_in_base.remove(tank_id)

                    self.__entities[new_position] = tank
                    del self.__entities[self.__tank_positions[tank_id]]
                    self.__tank_positions[tank_id] = new_position

                    if new_position in self.__base:
                        self.__tanks_in_base.append(tank_id)

                if action["action_type"] == Action.SHOOT:
                    tank: Tank = self.__entities[new_position]
                    if tank.reduce_hp():
                        spawn = tank.get_spawn_coordinate()
                        del self.__entities[new_position]
                        self.__entities[spawn] = tank
                        self.__tank_positions[tank.get_id()] = spawn
            return

        vehicles = game_state["vehicles"]
        for vehicle_id, vehicle_info in vehicles.items():
            vehicle_id = int(vehicle_id)
            new_position = Hex([vehicle_info["position"]["x"],
                                vehicle_info["position"]["y"],
                                vehicle_info["position"]["z"]])

            if vehicle_id in self.__tank_positions:
                old_position = self.__tank_positions[vehicle_id]
                if old_position == new_position:
                    # this tank did not move, only update hp and capture points
                    self.__entities[new_position].update(vehicle_info["health"], vehicle_info["capture_points"])
                else:
                    # this tank did move -> update its position and after that update its hp and capture points
                    tank = self.__entities[old_position]
                    if old_position in self.__base:
                        self.__tanks_in_base.remove(tank.get_id())

                    del self.__entities[old_position]
                    if new_position in self.__base:
                        # tank moved to the base, append it to tanks_in_base list
                        self.__tanks_in_base.append(tank.get_id())

                    # if light or hard repair was there, overwrite hex with this tank and
                    # update tank vehicle_info from server response
                    self.__entities[new_position] = tank

                    tank.update(vehicle_info["health"], vehicle_info["capture_points"])
                    self.__tank_positions[vehicle_id] = new_position

            else:
                # first occurrence; add this tank to entities and tanks hash map
                self.__tank_positions[vehicle_id] = new_position
                tank = Tank(vehicle_id, vehicle_info)
                self.__entities[new_position] = tank
                self.__tanks[vehicle_id] = tank

    def draw_map(self) -> None:
        # TODO: optimize, since special hexes are drawn twice and adjacent hexes have some same edges
        plt.figure()
        # draw the whole map
        for x in range(-self.__map_size + 1, self.__map_size):
            for y in range(-self.__map_size + 1, self.__map_size):
                z = -x - y
                if self.__map_size > z > -self.__map_size:
                    coords = Hex.get_corners([x, y, z])
                    coords.append(coords[0])
                    xs, ys = zip(*coords)
                    plt.plot(xs, ys, 'k')

        # draw base
        for h in self.__base:
            coords = Hex.get_corners(h.get_coordinates())
            coords.append(coords[0])
            xs, ys = zip(*coords)
            plt.plot(xs, ys, 'g')

        # draw entities
        for h, entity in self.__entities.items():
            color = "blue"
            if isinstance(entity, Tank):
                tank_dot = Hex.get_center(h.get_coordinates())
                plt.plot(tank_dot[0], tank_dot[1], marker='o', markersize='6',
                         markerfacecolor=color, markeredgewidth=0.0)
                continue

            entity_type = entity.get_type()
            if entity_type == "obstacle":
                color = "r"
            coords = Hex.get_corners(h.get_coordinates())
            coords.append(coords[0])
            xs, ys = zip(*coords)
            plt.plot(xs, ys, color)

        plt.axis('off')
        plt.pause(3)
        plt.show(block=False)
        plt.close("all")

    def get_dist(self, start: tuple, finish: tuple) -> float:
        x1, y1, z1 = start
        x2, y2, z2 = finish
        return round(((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)**0.5, 2)

    def move_to(self, who: tuple, where: tuple) -> dict:
        #TODO: Test for edge cases, have only tested with where = (0,0,0)
        moves = [(1, 0, -1), (0, 1, -1), (1, -1, 0),
                 (-1, 0, 1), (0, -1, 1), (-1, 1, 0)]

        old_positions = {tank_id: position.get_coordinates() for tank_id, position in self.__tank_positions.items() if
                         tank_id in who}

        possible_moves_by_tanks = []# [[(x,y,z), (x,y,z)]
        #                              [(x,y,z), (x,y,z)]] ordered by the same order that old positions has

        #TODO: I'm pretty sure that if a given tank cant make any moves this thing breaks but i'll fix it

        #Iterate through all the tanks and put all the possible moves all the tanks can make into possible_moves_by_tanks
        for tank_id, old_position in old_positions.items():
            possible_nexts = []
            for move in moves: # put hexs that are the shortest possible distance away from 'where' into possible_nexts
                new_position = old_position.copy()
                for i in range(3):
                    new_position[i] += move[i]

                if self.is_valid(Hex(new_position)) and new_position not in old_positions.values():
                    possible_nexts.append(new_position)

            possible_moves_by_tanks.append(possible_nexts)

        all_combinations = list(itertools.product(*possible_moves_by_tanks))# This creates all possible move combos

        sums_dists = [] # This calculates the sum of all the distances to 'where' of all the given tanks for all the
        for combination in all_combinations:# combinations of moves such that the lowest overall dist can be chosen
            sum_dist = 0
            for position in combination:
                sum_dist += self.get_dist(position, where)
            sums_dists.append(sum_dist)

        def has_repeating_lists(lst: List) -> bool: #THis function checks if there are repeating lists within a list
            for i, l1 in enumerate(lst):
                for j, l2 in enumerate(lst):
                    if i != j and l1 == l2:
                        return True
            return False

#TODO This while loop i bet can be done more efficiently by not adding combinations with repeating lists in the first place
        cnt = 0 #This loop removes combinations that have repeating lists which are coords of the future moves
        while cnt < len(all_combinations):
            positions = all_combinations[cnt]
            if has_repeating_lists(positions):
                all_combinations.pop(cnt)
                sums_dists.pop(cnt)
            else:
                cnt += 1

    #Choose the combination of moves with the overall shortest distance to 'where' and format appropiately
        best_combination = all_combinations[min(enumerate(sums_dists), key=lambda x: x[1])[0]]
        new_positions = {tank_id: best_combination[i] for i, tank_id in enumerate(old_positions)}

        return new_positions


    def shortest_path(self, start: Hex, end: Hex) -> [Hex]:
        """
        Determines the shortest path between two hexes
        :param start: start hex
        :param end: target hex
        :return: list of hexes that represent the shortest path
        """
        open_list = {start}
        closed_list = set()

        parent: dict = {start: None}

        movements = [
            Hex([1, 0, -1]),
            Hex([0, 1, -1]),
            Hex([1, -1, 0]),
            Hex([-1, 0, 1]),
            Hex([0, -1, 1]),
            Hex([-1, 1, 0])
        ]

        cheapest_path = defaultdict(lambda: float('inf'))
        cheapest_path[start] = 0

        def get_best() -> Hex:
            result, result_value = None, float('inf')
            for h in open_list:
                new_value = cheapest_path[h] + (h - end)
                if result is None or new_value < result_value:
                    result, result_value = h, new_value
            return result

        path_found = False
        while len(open_list) > 0:
            current = get_best()
            if current == end:
                path_found = True
                break
            for movement in movements:
                neighbour = current + movement
                if not self.is_valid(neighbour) or \
                        (neighbour in self.__entities and self.__entities[neighbour].get_type() == 'obstacle'):
                    continue
                path_to_neighbour_weight = cheapest_path[current] + 1
                if neighbour not in open_list and neighbour not in closed_list:
                    open_list.add(neighbour)
                    parent[neighbour] = current
                    cheapest_path[neighbour] = path_to_neighbour_weight
                elif path_to_neighbour_weight < cheapest_path[neighbour]:
                    parent[neighbour] = current
                    cheapest_path[neighbour] = path_to_neighbour_weight
                    if neighbour in closed_list:
                        closed_list.remove(neighbour)
                        open_list.add(neighbour)

            open_list.remove(current)
            closed_list.add(current)

        if path_found:
            path: [Hex] = []
            while end is not None:
                path.append(end)
                end = parent[end]
            path.reverse()
            return path
        else:
            return None

    def is_valid(self, target_hex: Hex) -> bool:
        """
        Checks if hex is valid for the current map
        :param target_hex:
        :return: True if valid, False otherwise
        """
        coords = target_hex.get_coordinates()
        if sum(coords) != 0:
            return False

        return not any(coords[i] >= self.__map_size or coords[i] <= -self.__map_size for i in range(3))

    def is_tank_in_base(self, tank_id: int) -> bool:
        return tank_id in self.__tanks_in_base

    def set_entity(self, hex_coord: Hex, entity: Entity) -> None:
        self.__entities[hex_coord] += entity

    def get_tank_position(self, tank_id: int) -> Hex:
        return self.__tank_positions[tank_id]

    def get_entities(self) -> dict:
        return self.__entities

    def get_base(self) -> [Hex]:
        return self.__base

    def get_entity_at(self, hex_pos: Hex):
        if hex_pos in self.__entities:
            return self.__entities[hex_pos]
        return None
