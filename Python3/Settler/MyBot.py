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

VERSION = "0.9.3"
DEBUG = False

def closest_target_from_list(gamemap, source, target_list, range=1000):
    #find closest enemy ignoring obstacles
    closest = None
    for foreign_entity in target_list:
        if source.owner == foreign_entity.owner:
            continue
        distance = source.calculate_distance_between(foreign_entity)
        if distance < range:
            range = distance
            closest = foreign_entity
    return closest

def find_nearby_target(gamemap, entity, range=40):
    logger = logging.getLogger(__name__)
    all_nearby = gamemap.nearby_entities_by_distance(entity)
    if len(all_nearby) == 0:
        return None
    logger.debug("nearby_entities_by_distance(entity={}) len: {}"
                 .format(entity.id, len(all_nearby)))
    try:
        index = 0
        for key in all_nearby.keys():
            nearby_entity = all_nearby[key][0]
            if 'Ship' == nearby_entity.__class__.__name__:
                logger.debug("nearby from {},{}: {}, {} x,y {},{}"
                             .format(entity.x, entity.y,
                                     nearby_entity.__class__.__name__,
                                     nearby_entity, 
                                     nearby_entity.x, nearby_entity.y))
                return nearby_entity
    except KeyError:
        pass
    return None

def find_closest_unowned_planet(gamemap, ship, planetlist, range=1000):
    logger = logging.getLogger(__name__)
    best_planet = None
    logger.debug(" ship: {} find_closest_unowned_planet, len planetlist: {}"
                 .format(ship.id, len(planetlist)))
    for planet in planetlist:
        distance = ship.calculate_distance_between(planet)
        logger.debug(" ship: {} planet: {} distance: {:.02f}, prior: {:.02f}"
                     .format(ship.id, planet.id, distance, range))
        if distance < range:
            best_planet = planet
            range = distance
    return best_planet

def planet_dock_if_nearby(gamemap, ship):
    for planet in gamemap.all_planets():
        if ship.can_dock(planet) and not planet.is_owned():
            return planet
        if planet.owner == ship.owner and not planet.is_full() and ship.can_dock(planet):
            return planet

def avoid_collision_with_list(ship, entity_list):
    '''Given a list of ships, compute destination away from center'''
    center = hlt.entity.Position((sum(entity.x for entity in entity_list)/len(entity_list)),
                                 (sum(entity.y for entity in entity_list)/len(entity_list)))
    # now we compute the anti-position for a closest_point_to analog
    target = hlt.entity.Position((2*ship.x - center.x),
                                 (2*ship.y - center.y))
    return target

def navigate(ship, destination, game_map, speed=hlt.constants.MAX_SPEED/2, ignore_ships=True):
    return ship.navigate(destination, game_map, speed, ignore_ships=ignore_ships)

def halite2_main():
    logger = logging.getLogger(__name__)
    # GAME START
    # Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
    game = hlt.Game("Settler %s" % VERSION)
    turn = 0
    
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
        my_ships = game_map.get_me().all_ships()
        my_docked_ships = [s for s in my_ships if s.docking_status != s.DockingStatus.UNDOCKED]
        my_undocked_ships = [s for s in my_ships if s.docking_status == s.DockingStatus.UNDOCKED]
        logger.info("turn: {} enemy: {} enemy docked: {} my ships: {} my undocked: {}"
                     .format(turn, len(enemy_ships), len(enemy_docked_ships),
                             len(my_ships), len(my_undocked_ships)))
    
        # ship_time_limit: total seconds permitted
        # ship_speed: limit navigation speed
        # ship_action_limit: total permitted navigate calls or other expensive checks
        # action_ships: give the above limit, these ships will act this turn
        #               sample/shuffle ships to avoid deadlocks
        # action_planet_percent: percentage of above (based on id hash) that will dock
        #               or move to planets
        if turn > 200 or len(my_undocked_ships) > 100:
            ship_time_limit = 1.5
            ship_speed = hlt.constants.MAX_SPEED*0.4
            ship_action_limit = 50
            ship_dock_ratio = 5
            ship_dock_enemy_range = 6
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            action_ship_long_range = 50
            action_planet_percent = 15
            action_docked_percent = 15
            action_target_docked_range = 50
            navigate_ignore_ships_threshold = 100
        elif turn > 100 and len(my_undocked_ships) > 100:
            ship_time_limit = 1.6
            ship_speed = hlt.constants.MAX_SPEED*0.5
            ship_action_limit = 70
            ship_dock_ratio = 4
            ship_dock_enemy_range = 7
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            action_ship_long_range = 100
            action_planet_percent = 15
            action_docked_percent = 15
            action_target_docked_range = 50
            navigate_ignore_ships_threshold = 100
        elif turn > 50:
            ship_time_limit = 1.8
            ship_speed = hlt.constants.MAX_SPEED*0.95
            ship_action_limit = 100
            ship_dock_ratio = 2
            ship_dock_enemy_range = 10
            ship_shun_center_planets = False
            action_ships = my_undocked_ships[:min(ship_action_limit, len(my_undocked_ships))]
            action_ship_long_range = 100
            action_planet_percent = 70
            action_docked_percent = 70
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100
        elif turn > 10:
            ship_time_limit = 1.9
            ship_speed = hlt.constants.MAX_SPEED
            ship_action_limit = 100
            ship_dock_ratio = 1
            ship_dock_enemy_range = 10
            ship_shun_center_planets = False
            action_ships = my_undocked_ships
            action_ship_long_range = 50
            action_planet_percent = 75
            action_docked_percent = 75
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100
        else:
            ship_time_limit = 1.9
            ship_speed = hlt.constants.MAX_SPEED
            ship_action_limit = 100
            ship_dock_ratio = 1
            ship_dock_enemy_range = 20
            ship_shun_center_planets = True
            action_ships = sample(my_undocked_ships, min(ship_action_limit, len(my_undocked_ships)))
            action_ship_long_range = 50
            action_planet_percent = 90
            action_docked_percent = 0
            action_target_docked_range = 100
            navigate_ignore_ships_threshold = 100

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
        #only 1 ship can dock per turn, so limit our attempts?
        planet_docking = []
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        for ship in action_ships:
            if (time.time() - turn_start_time) > ship_time_limit:
                logger.debug("turn: {} ship: {} skipping due to time {}"
                             .format(turn, ship.id, (time.time() - turn_start_time)))
                break

            # limit the number of ships we look at per turn, just in case
            ship_actions += 1
            if ship_actions > ship_action_limit:
                logger.debug("turn: {} ship: {} skipping due to ship actions {} after {:.03f} seconds"
                             .format(turn, ship.id, ship_actions, time.time() - turn_start_time))
                continue
    
            if turn == 1:
                avoidance = avoid_collision_with_list(ship, my_undocked_ships)
                logger.debug("turn: {} ship: {} collision avoidance: {},{}"
                             .format(turn, ship.id, avoidance.x, avoidance.y))
                navigate_command = ship.navigate(avoidance,
                                                 game_map, speed = hlt.constants.MAX_SPEED,
                                                 ignore_ships=False)
                if navigate_command:
                    command_queue.append(navigate_command)
                continue
                
            # if we're next to a planet, maybe do that
            elif ship_dock_ratio == 1 or randint(0, ship_dock_ratio-1) == 0:
                # before docking check for nearby enemies
                target_ship = closest_target_from_list(game_map, ship, 
                                                       enemy_ships, ship_dock_enemy_range)
                if target_ship:
                    logger.info("turn: {} ship: {} defensive targetting ship: {}"
                                .format(turn, ship.id, target_ship.id))
                    navigate_command = ship.navigate(ship.closest_point_to(target_ship, 4.5),
                                                     game_map, speed = hlt.constants.MAX_SPEED,
                                                     ignore_ships=ignore_ships)
                    if navigate_command:
                        command_queue.append(navigate_command)
                    continue
                if not target_ship:
                    docking_target = planet_dock_if_nearby(game_map, ship)
                    if docking_target:
                        if docking_target.id not in planet_docking:
                            logger.info("turn: {} ship: {} docking to planet: {}"
                                        .format(turn, ship.id, docking_target.id))
                            planet_docking.append(docking_target.id)
                            command_queue.append(ship.dock(docking_target))
                        # this will not fall through and instead wait a turn and check again
                        continue
                    # else fall through to planet/ship navigation

            if hash(ship.id) % 100 < action_planet_percent:
                # find ship's closest planet to navigate to
                logger.debug("ship id {} hash {} is planet action (percent: {})"
                             .format(ship.id, hash(ship.id) % 100, action_planet_percent))
                planet = find_closest_unowned_planet(game_map, ship, unowned_planets, 100)
                if planet:
                    logger.info("turn: {} ship: {} x,y {},{} off to planet: {} x,y {},{}"
                                .format(turn, ship.id, ship.x, ship.y,
                                        planet.id, planet.x, planet.y))
                    target_point = ship.closest_point_to(planet)
                    navigate_command = ship.navigate(target_point, game_map, 
                                                     speed=ship_speed, 
                                                     ignore_ships=ignore_ships)
                    if ship_shun_center_planets and planet.id < 4:
                        logger.debug("planet: {} used when shunned".format(planet.id))
                    if navigate_command:
                        command_queue.append(navigate_command)
                    unowned_planets.remove(planet)
                    continue
                # else this will fall through to aggressive ship behavior

            # anti-ship action 
            logger.debug("ship id {} hash {} is ship action"
                         .format(ship.id, hash(ship.id) % 100))
            if hash(ship.id) % 100 < action_docked_percent and len(enemy_docked_ships) > 0:
                time_1 = time.time()
                target_ship = closest_target_from_list(game_map, ship, 
                                                       enemy_docked_ships,
                                                       action_target_docked_range)
                if target_ship:
                    logger.debug("ship: {} targetting docked closest id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id, 
                                         target_ship.id, target_ship.x, target_ship.y,
                                         time.time() - time_1))
            if not target_ship and hash(ship.id) % 100 < action_ship_long_range:
                time_1 = time.time()
                target_ship_1 = closest_target_from_list(game_map, ship, enemy_ships, 200)
                if target_ship_1:
                    logger.debug("ship: {} targetting closest returned id,x,y {},{},{} in {:.06f}"
                                 .format(ship.id, 
                                         target_ship_1.id, target_ship_1.x, target_ship_1.y,
                                         time.time() - time_1))

            if target_ship:
                logger.info("turn: {} ship: {} targetting ship: {}"
                            .format(turn, ship.id, target_ship.id))
                distance = 2.75 + (ship.id % 3)*0.5
                navigate_command = ship.navigate(ship.closest_point_to(target_ship, distance),
                                                 game_map, speed=ship_speed,
                                                 ignore_ships=ignore_ships)
                if navigate_command:
                    command_queue.append(navigate_command)
            else:     
                logger.info("turn: {} ship: {} no work".format(turn, ship.id))
    
        # Send our set of commands to the Halite engine for this turn
        turn_end_presend = time.time()
        logger.info("turn: {} end ships time: {:.03f}"
                         .format(turn, turn_end_presend - turn_start_time))
        game.send_command_queue(command_queue)
        #logger.debug("turn: {} send_command_queue len: {} took: {:.03f}"
        #             .format(turn, len(command_queue), time.time() - turn_end_presend))
        logger.info("turn: {} end, took: {:.03f}"
                    .format(turn, time.time() - turn_start_time))
        # TURN END
    # GAME END

if __name__ == "__main__":
        #logging.basicConfig(level=logging.INFO)
        halite2_main()
