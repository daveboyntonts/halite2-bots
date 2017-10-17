"""
Modified Settler Bot
"""
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
import time
from datetime import datetime
import logging
import pprint

from random import sample, randint
from collections import defaultdict

VERSION = "0.9.4"
DEBUG = False


def closest_target_from_list(gamemap, source, target_list, max_distance=1000):
    '''find closest entity to an source entity using a calculate_distance_between loop'''
    logger = logging.getLogger(__name__)
    best_target = None
    best_distance = max_distance
    for foreign_entity in target_list:
        if source.owner == foreign_entity.owner:
            continue
        distance = source.calculate_distance_between(foreign_entity)
        if distance < best_distance:
            best_target = foreign_entity
            best_distance = distance
    return best_target


def find_nearby_target(gamemap, entity, max_distance=40):
    '''find closest ship to an entity using nearby_entities_by_distance'''
    logger = logging.getLogger(__name__)
    all_nearby = gamemap.nearby_entities_by_distance(entity)
    if len(all_nearby) == 0:
        return None
    try:
        index = 0
        for key in all_nearby.keys():
            if key > max_distance:
                break
            nearby_entity = all_nearby[key][0]
            if 'Ship' == nearby_entity.__class__.__name__:
                return nearby_entity
    except KeyError:
        pass
    return None


def find_closest_owned_planet_with_docking(game_map, ship, planetlist, max_distance=1000, already_targetted=None):
    '''find one of my planets that has open docking slots, not including ships in docking process'''
    logger = logging.getLogger(__name__)
    best_planet = None
    best_distance = max_distance
    try:
        for planet in planetlist:
            distance = ship.calculate_distance_between(planet)
            targetted = 0 if not already_targetted else already_targetted[planet.id]
            if (distance < best_distance and ship.owner == planet.owner and
                        planet.num_docking_spots > len(planet._docked_ships) + targetted):
                best_planet = planet
                best_distance = distance
        if best_planet:
            logger.debug("find_closest_owned_planet_with_docking ship: {} returning planet {} distance {} max,current {},{}"
                         .format(ship.id, best_planet.id, best_distance,
                                 best_planet.num_docking_spots, len(best_planet._docked_ships)))
    except TypeError as exc:
        logger.error("find_closest_owned_planet_with_docking(,{},{},{},{}) returning due to error: {}"
                     .format(ship.id, len(planetlist), len(already_targetted), max_distance, str(exc)))
    return best_planet


def find_closest_owned_planet(game_map, ship, planetlist, max_distance=1000):
    '''find one of my planets'''
    logger = logging.getLogger(__name__)
    best_planet = None
    best_distance = max_distance
    for planet in planetlist:
        distance = ship.calculate_distance_between(planet)
        if (distance < best_distance and ship.owner == planet.owner):
            best_planet = planet
            best_distance = distance
            logger.debug("ship: {} updating closest planet {} distance {}"
                         .format(ship.id, planet.id, distance,
                                 planet.num_docking_spots, len(planet._docked_ships)))
    if best_planet:
        logger.debug("find_closest_owned_planet_with_docking ship: {} returning planet {} distance {} max,current {},{}"
                     .format(ship.id, best_planet.id, best_distance,
                             best_planet.num_docking_spots, len(best_planet._docked_ships)))
    return best_planet


def find_closest_unowned_planet(gamemap, ship, planetlist, max_distance=1000):
    logger = logging.getLogger(__name__)
    best_planet = None
    best_distance = max_distance
    for planet in planetlist:
        distance = ship.calculate_distance_between(planet)
        if distance < best_distance:
            best_planet = planet
            best_distance = distance
    if best_planet:
        logger.debug(" ship: id,x,y {},{},{} find_closest_unowned_planet: id,x,y {},{},{}"
                     .format(ship.id, ship.x, ship.y,
                             best_planet.id, best_planet.x, best_planet.y))
    return best_planet


def nearby_planet_if_dockable(gamemap, ship):
    for planet in gamemap.all_planets():
        if ship.can_dock(planet) and not planet.is_owned():
            return planet
        if planet.owner == ship.owner and not planet.is_full() and ship.can_dock(planet):
            return planet


def navigate_away_from_list(source, entity_list):
    '''Given a list of ships, compute destination away from center'''
    logger = logging.getLogger(__name__)
    target = None
    try:
        sum_x = 0
        sum_y = 0
        for entity in entity_list:
            sum_x += entity.x
            sum_y += entity.y
        center = hlt.entity.Position(sum_x / len(entity_list), sum_y / len(entity_list))
        # now we compute the anti-position for a closest_point_to analog
        target = hlt.entity.Position((2 * source.x - center.x),
                                     (2 * source.y - center.y))
        logger.debug("navigate_away: source x,y {},{} target x,y {},{}"
                     .format(source.x, source.y, target.x, target.y))
    except AttributeError as exc:
        logger.debug("navigate_away: returning None due to Attribute error: {}"
                     .format(str(exc)))
    return target


def navigate_away_from_dict(source, entity_dict):
    '''Given a dict with key=id, value=entity, compute destination away from center'''
    logger = logging.getLogger(__name__)
    target = None
    if not type(entity_list) is dict:
        logger.error("navigate_away_from_dict called incorrectly with source {}, thing {}"
                     .format(source.id, pprint.pformat(entity_dict)))
        return None
    try:
        sum_x = 0
        sum_y = 0
        for obj in entity_list:
            sum_x += entity_list[obj].x
            sum_y += entity_list[obj].y
        center = hlt.entity.Position(sum_x / len(entity_list), sum_y / len(entity_list))
        # now we compute the anti-position for a closest_point_to analog
        target = hlt.entity.Position((2 * source.x - center.x),
                                     (2 * source.y - center.y))
        logger.debug("navigate_away: source x,y {},{} target x,y {},{}"
                     .format(source.x, source.y, target.x, target.y))
    except AttributeError as exc:
        logger.debug("navigate_away: returning None due to Attribute error: {}"
                     .format(str(exc)))
    return target


def navigate(ship, destination, game_map, speed=hlt.constants.MAX_SPEED / 2, ignore_ships=True):
    return ship.navigate(destination, game_map, speed, ignore_ships=ignore_ships)


def halite2_main():
    logger = logging.getLogger(__name__)
    # GAME START
    # Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
    game = hlt.Game("Settler %s" % VERSION)
    turn = 0

    # save ship_skip_list between turns
    ship_skip_list = list()

    while True:
        # TURN START
        # Update the map for the new turn and get the latest version

        turn_start_time = time.time()
        turn += 1

        logger.info("turn: {} start at: {}".format(turn, datetime.now().isoformat('T')))
        game_map = game.update_map()
        logger.info("turn: {} game.update_map took: {}"
                    .format(turn, time.time() - turn_start_time))

        #
        # variables that may factor in policy
        #
        enemy_ships = [s for s in game_map._all_ships() if s.owner != game_map.get_me()]
        enemy_docked_ships = [s for s in enemy_ships if s.docking_status != s.DockingStatus.UNDOCKED]
        enemy_undocked_ships = [s for s in enemy_ships if s.docking_status == s.DockingStatus.UNDOCKED]
        enemy_owned_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner != game_map.get_me()]

        my_ships = game_map.get_me().all_ships()
        my_docked_ships = [s for s in my_ships if s.docking_status != s.DockingStatus.UNDOCKED]
        my_undocked_ships = [s for s in my_ships
                             if s.docking_status == s.DockingStatus.UNDOCKED
                             and s.id not in ship_skip_list]
        ship_skip_list = list()

        logger.info("turn: {} enemy: {} enemy docked: {} my ships: {} my undocked: {}"
                    .format(turn, len(enemy_ships), len(enemy_docked_ships),
                            len(my_ships), len(my_undocked_ships)))

        #
        # defaults which may not need tuning
        #
        planet_navigate_distance = 2
        ship_navigate_distance = 2

        # ship_time_limit: total seconds permitted
        # ship_speed: limit navigation speed
        # ship_action_limit: total permitted navigate calls or other expensive checks
        # action_ships: give the above limit, these ships will act this turn
        #               sample/shuffle ships to avoid deadlocks

        # e.g. action_planet_percent: percentage of above (based on id hash) that will dock
        # percents have order:
        #   action_destroy_planet_percent 
        #   action_planet_percent 
        #   action_collide_docked_percent
        #   action_target_docked_percent 

        if turn > 200 and len(my_undocked_ships) > 100:
            ship_time_limit = 1.8
            ship_speed = hlt.constants.MAX_SPEED * 0.4
            ship_action_limit = 40
            ship_dock_ratio = 4
            ship_dock_enemy_range = 6
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            #action_ship_long_range = int(max(1000, game_map.width, game_map.height))
            action_ship_long_range = 50
            action_planet_long_range = int(max(1000, game_map.width, game_map.height))
            action_planet_target_limit = 2
            action_target_docked_range = 1000
            navigate_ignore_ships_threshold = 100
            action_destroy_planet_percent = 25
            action_planet_percent = 40
            action_collide_docked_percent = 60
            action_target_docked_percent = 70
        elif turn > 100 and len(my_undocked_ships) > 100:
            ship_time_limit = 1.8
            ship_speed = hlt.constants.MAX_SPEED * 0.5
            ship_action_limit = 60
            ship_dock_ratio = 3
            ship_dock_enemy_range = 7
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            #action_ship_long_range = int(max(game_map.width, game_map.height) / 2)
            action_ship_long_range = 100
            action_planet_long_range = int(max(game_map.width, game_map.height) / 2)
            action_planet_target_limit = 0
            action_target_docked_range = 150
            navigate_ignore_ships_threshold = 100
            action_destroy_planet_percent = 15
            action_planet_percent = 30
            action_collide_docked_percent = 55
            action_target_docked_percent = 80
        elif turn > 50:
            ship_time_limit = 1.8
            ship_speed = hlt.constants.MAX_SPEED * 0.95
            ship_action_limit = 100
            ship_dock_ratio = 2
            ship_dock_enemy_range = 10
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            action_ship_long_range = 100
            action_planet_long_range = 100
            action_planet_target_limit = 0
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100
            action_destroy_planet_percent = 0
            action_planet_percent = 50
            action_collide_docked_percent = 65
            action_target_docked_percent = 90
        elif turn > 10:
            ship_time_limit = 1.9
            ship_speed = hlt.constants.MAX_SPEED
            ship_action_limit = 100
            ship_dock_ratio = 1
            ship_dock_enemy_range = 10
            ship_shun_center_planets = False
            action_ships = my_undocked_ships
            action_ship_long_range = 50
            action_planet_long_range = 200
            action_planet_target_limit = 0
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100
            action_destroy_planet_percent = 0
            action_planet_percent = 75
            action_collide_docked_percent = 0
            action_target_docked_percent = 95
        else:
            ship_time_limit = 1.9
            ship_speed = hlt.constants.MAX_SPEED
            ship_action_limit = 100
            ship_dock_ratio = 1
            ship_dock_enemy_range = 20
            ship_shun_center_planets = True
            action_ships = sample(my_undocked_ships, min(ship_action_limit, len(my_undocked_ships)))
            action_ship_long_range = 50
            action_planet_long_range = 100
            action_planet_target_limit = 2
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100
            action_destroy_planet_percent = 0
            action_planet_percent = 90
            action_collide_docked_percent = 0
            action_target_docked_percent = 0

        action_ships.sort(key=lambda x: x.id)
        owned_planets = [p for p in game_map.all_planets() if p.owner == game_map.get_me()]
        unowned_planets = [p for p in game_map.all_planets() if not p.is_owned()]
        unowned_planets.sort(key=lambda x: x.id)
        if ship_shun_center_planets:
            unowned_planets = [p for p in unowned_planets if p.id > 3]

        if len(my_undocked_ships) + len(enemy_undocked_ships) > navigate_ignore_ships_threshold:
            ignore_ships = True
        else:
            ignore_ships = False

        logger.info("turn: {} end of prep, start of ship loop after: {:.03f}"
                    .format(turn, (time.time() - turn_start_time)))

        #
        # local variables
        #
        ship_actions = 0
        ship_nowork = 0
        ship_dockwait = 0

        # limit number of ships docking to the same planet
        planet_docking = dict()
        for p in game_map.all_planets():
            planet_docking[p.id] = p.num_docking_spots - len(p._docked_ship_ids)
        # limit number of ships navigating to the same planet
        planet_targetting = defaultdict(int)
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        for ship in action_ships:
            if (time.time() - turn_start_time) > ship_time_limit:
                logger.warn("turn: {} ship: {} skipping due to time {}"
                            .format(turn, ship.id, (time.time() - turn_start_time)))
                break

            # limit the number of ships we look at per turn, just in case
            ship_actions += 1
            if ship_actions > ship_action_limit:
                logger.warn("turn: {} ship: {} skipping due to ship actions {} after {:.03f} seconds"
                            .format(turn, ship.id, ship_actions, time.time() - turn_start_time))
                continue

            if turn == 1:
                logger.debug("turn: {} ship: {} calling with my_undocked_ships: {}"
                             .format(turn, ship.id, pprint.pformat(my_undocked_ships)))
                avoidance = navigate_away_from_list(ship, my_undocked_ships)
                logger.debug("turn: {} ship: {} collision avoidance: {},{}"
                             .format(turn, ship.id, avoidance.x, avoidance.y))
                navigate_command = ship.navigate(avoidance,
                                                 game_map, speed=hlt.constants.MAX_SPEED,
                                                 ignore_ships=False)
                if navigate_command:
                    command_queue.append(navigate_command)
                continue

            # Before docking check for nearby enemies
            target_ship = closest_target_from_list(game_map, ship,
                                                   enemy_ships, ship_dock_enemy_range)
            if target_ship:
                logger.info("turn: {} ship: {} defensive targetting ship: {}"
                            .format(turn, ship.id, target_ship.id))
                navigate_command = ship.navigate(ship.closest_point_to(target_ship, ship_navigate_distance),
                                                 game_map, speed=ship_speed,
                                                 ignore_ships=ignore_ships)
                if navigate_command:
                    command_queue.append(navigate_command)
                continue

            # if we're next to a planet, maybe do that
            #if ship_dock_ratio > 0 and (hash(ship.id) % ship_dock_ratio) == 0:
            if ship_dock_ratio == 1 or randint(0, ship_dock_ratio-1) == 0:
                logger.debug("ship id {} hash {} checking for dock, ship_dock_ratio {}"
                             .format(ship.id, hash(ship.id) % 100, ship_dock_ratio))
                docking_target = nearby_planet_if_dockable(game_map, ship)
                if docking_target:
                    if planet_docking[docking_target.id] > 0:
                        logger.info("turn: {} ship: {} docking to planet: {}"
                                    .format(turn, ship.id, docking_target.id))
                        planet_docking[docking_target.id] -= 1
                        command_queue.append(ship.dock(docking_target))
                    else:
                        ship_dockwait += 1
                        # this will not fall through and instead wait a turn and check again
                    continue
                # else fall through to planet/ship navigation

            if hash(ship.id) % 100 < action_destroy_planet_percent: 
                # move to an enemy planet
                logger.debug("ship: {} targetting the planet! ...".format(ship.id))
                time_1 = time.time()
                planet = closest_target_from_list(game_map, ship, enemy_owned_planets, action_planet_long_range)
                if planet:
                    logger.debug("ship: {} targetting closest returned planet id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id, planet.id, planet.x, planet.y, time.time() - time_1))
                    target_point = ship.closest_point_to(planet, -1)
                    navigate_command = ship.navigate(target_point, game_map,
                                                     speed=hlt.constants.MAX_SPEED,
                                                     ignore_ships=True)
                    if navigate_command:
                        command_queue.append(navigate_command)
                        continue
                # else fall through

            if hash(ship.id) % 100 < action_planet_percent:
                # find ship's closest planet to navigate to
                logger.debug("ship id {} hash {} is planet action (percent: {})"
                             .format(ship.id, hash(ship.id) % 100, action_planet_percent))
                # TODO: reverse order
                planet = find_closest_unowned_planet(game_map, ship, unowned_planets, 100)
                if not planet:
                    planet = find_closest_owned_planet_with_docking(game_map, ship, owned_planets,
                                                                    action_planet_long_range,
                                                                    planet_targetting)
                if planet:
                    logger.info("turn: {} ship: {} x,y {},{} off to planet: {} x,y {},{}"
                                .format(turn, ship.id, ship.x, ship.y,
                                        planet.id, planet.x, planet.y))
                    target_point = ship.closest_point_to(planet, planet_navigate_distance)
                    navigate_command = ship.navigate(target_point, game_map,
                                                     speed=ship_speed,
                                                     ignore_ships=ignore_ships)
                    if ship_shun_center_planets and planet.id < 4:
                        logger.debug("planet: {} used when shunned".format(planet.id))
                    if navigate_command:
                        command_queue.append(navigate_command)
                    if action_planet_target_limit > 0:
                        planet_targetting[planet.id] += 1
                        if (not planet.is_owned() and
                                planet_targetting[planet.id] > (planet.num_docking_spots)):
                            unowned_planets.remove(planet)
                    continue

                # else this will fall through to aggressive anti-ship behavior

            # anti-ship action 
            logger.debug("ship id {} hash {} is ship action"
                         .format(ship.id, hash(ship.id) % 100))
            if hash(ship.id) % 100 < action_collide_docked_percent and len(enemy_docked_ships) > 0:
                logger.debug("ship: {} colliding with docked ...".format(ship.id))
                time_1 = time.time()
                target_planet = closest_target_from_list(game_map, ship,
                                                         enemy_owned_planets,
                                                         action_target_docked_range)
                if target_planet:
                    target_ship_index = hash(ship.id) % len(target_planet._docked_ship_ids)
                    target_ship = target_planet._docked_ships[target_planet._docked_ship_ids[target_ship_index]]
                    logger.debug("ship: {} targetting planet {} docked id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id, target_planet.id,
                                         target_ship.id, target_ship.x, target_ship.y,
                                         time.time() - time_1))
                    navigate_command = ship.navigate(ship.closest_point_to(target_ship, 0),
                                                     game_map, speed=ship_speed,
                                                     ignore_ships=True)
                    if navigate_command:
                        command_queue.append(navigate_command)
                        continue
                # else fall through

            if hash(ship.id) % 100 < action_target_docked_percent and len(enemy_docked_ships) > 0:
                time_1 = time.time()
                target_planet = closest_target_from_list(game_map, ship,
                                                         enemy_owned_planets,
                                                         action_target_docked_range)
                if target_planet:
                    target_ship_index = hash(ship.id) % len(target_planet._docked_ship_ids)
                    target_ship = target_planet._docked_ships[target_planet._docked_ship_ids[target_ship_index]]
                    logger.debug("ship: {} targetting planet {} docked id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id, target_planet.id,
                                         target_ship.id, target_ship.x, target_ship.y,
                                         time.time() - time_1))
            else:
                logger.debug("ship: {} hash {} not less than {} or no docked ships"
                             .format(ship.id, hash(ship.id) % 100, action_target_docked_percent))

            if not target_ship:
                time_1 = time.time()
                target_ship = closest_target_from_list(game_map, ship, enemy_ships, action_ship_long_range)
                if target_ship:
                    logger.debug("ship: {} targetting closest returned id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id,
                                         target_ship.id, target_ship.x, target_ship.y,
                                         time.time() - time_1))
                else:
                    logger.debug("ship: {} didn't find closest_target_from_list(,,len={},range={})"
                                 .format(ship.id, len(enemy_ships), action_ship_long_range))
                    maybe_ship = closest_target_from_list(game_map, ship, enemy_ships, 2000)
                    if maybe_ship:
                        logger.debug("ship: {} would've found ship: {} at x,y {},{} distance {}"
                                     .format(ship.id, maybe_ship.id, maybe_ship.x, maybe_ship.y,
                                             ship.calculate_distance_between(maybe_ship)))

            if target_ship:
                logger.info("turn: {} ship: {} targetting ship: {}"
                            .format(turn, ship.id, target_ship.id))
                distance = ship_navigate_distance + (ship.id % 3) * 0.5
                navigate_command = ship.navigate(ship.closest_point_to(target_ship, distance),
                                                 game_map, speed=ship_speed,
                                                 ignore_ships=ignore_ships)
                if navigate_command:
                    command_queue.append(navigate_command)
            else:
                ship_nowork += 1
                ship_skip_list.append(ship.id)  # skip check next turn
                logger.debug("turn: {} ship: {} at x,y {},{} no work"
                             .format(turn, ship.id, ship.x, ship.y))

        # Send our set of commands to the Halite engine for this turn
        turn_end_presend = time.time()
        logger.info("turn: {} end ships time: {:.03f} actions {} dockwait {} nowork {}"
                    .format(turn, turn_end_presend - turn_start_time, ship_actions, ship_dockwait, ship_nowork))
        game.send_command_queue(command_queue)
        # logger.debug("turn: {} send_command_queue len: {} took: {:.03f}"
        #             .format(turn, len(command_queue), time.time() - turn_end_presend))
        logger.info("turn: {} end, took: {:.03f}"
                    .format(turn, time.time() - turn_start_time))
        # TURN END
        # GAME END


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    halite2_main()
