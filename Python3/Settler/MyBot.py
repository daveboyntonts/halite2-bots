"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
import time
from datetime import datetime
import logging
import pprint

from random import sample, randint

DEBUG = False

def closest_enemy(gamemap, myship):
    #find closest enemy ignoring obstacles
    range = 100
    closest = None
    for foreign_entity in gamemap._all_ships():
        if myship.owner == foreign_entity.owner:
            continue
        distance = myship.calculate_distance_between(foreign_entity)
        if distance < range:
            range = distance
            closest = foreign_entity
    return closest

def find_closest_target(gamemap, ship):
    logger = logging.getLogger(__name__)
    nearby = gamemap.nearby_entities_by_distance(ship)
    if DEBUG:
        logger.debug(pprint.pformat(nearby.keys()))
    return None

def find_closest_unowned_planet(gamemap, ship, planetlist):
    logger = logging.getLogger(__name__)
    range = gamemap.width + gamemap.height
    best_planet = None
    if DEBUG:
        logger.debug("ship: {} find_closest_unowned_planet, len planetlist: {}".format(ship.id, len(planetlist)))
    for planet in planetlist:
        distance = ship.calculate_distance_between(planet)
        if DEBUG:
            logger.debug("ship: {} planet: {} distance: {:.02f}, prior: {:.02f}"
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
            # only let half of spawned ships dock
            if (ship.id % 2) == 0:
                return planet

def navigate(ship, destination, game_map, speed=hlt.constants.MAX_SPEED/2, ignore_ships=True):
    return ship.navigate(destination, game_map, speed, ignore_ships=ignore_ships)

def halite2_main():
    logger = logging.getLogger(__name__)
    # GAME START
    # Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
    game = hlt.Game("Settler 0.9")
    turn = 0
    
    #persist between turns key=ship_id, value=planet_id
    ship_target = {}
    
    while True:
        # TURN START
        # Update the map for the new turn and get the latest version
        
        turn_start_us = time.time()
        turn += 1
        logger.info("turn: {} start at: {}".format(turn, datetime.now().isoformat('T')))

        game_map = game.update_map()
    
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []
    
        #only 1 ship can dock per turn?
        unowned_planets = [p for p in game_map.all_planets() if not p.is_owned()]
        unowned_planets.sort(key=lambda x: x.id) 
        planet_docking = []
    
        ship_time_limit = 1.7
        ship_speed = hlt.constants.MAX_SPEED*0.8
        ship_action_limit = 80
        ship_actions = 0
    
        enemy_ships = [s for s in game_map._all_ships() if s.owner != game_map.get_me()]
        docked_enemy_ships = [s for s in enemy_ships if s.docking_status == s.DockingStatus.DOCKED]
        # every ship that I control
        all_ships = game_map.get_me().all_ships()
        undocked_ships = [s for s in all_ships if s.docking_status == s.DockingStatus.UNDOCKED]
        if DEBUG:
            logger.debug("enemy: {} enemy docked: {} my undocked: {}"
                         .format(len(enemy_ships), len(docked_enemy_ships), len(undocked_ships)))
    
        if len(all_ships) > 50:
            ignore_ships = True
        else:
            ignore_ships = False
    
        # sample/shuffle ships to avoid deadlocks
        for ship in sample(undocked_ships, min(ship_action_limit, len(undocked_ships))):
            if (time.time() - turn_start_us) > ship_time_limit:
                logger.info("turn: {} ship: {} skipping due to time {}"
                            .format(turn, ship.id, (time.time() - turn_start_us)))
                continue

            # limit the number of ships we look at per turn, just in case
            ship_actions += 1
            if ship_actions > ship_action_limit:
                logger.info("turn: {} ship: {} skipping due to ship actions {} after {:.03f} seconds"
                            .format(turn, ship.id, ship_actions, time.time() - turn_start_us))
                continue
    
            # check for nearby dockable planets up to the max
            planet = planet_dock_if_nearby(game_map, ship)
            if planet:
                if planet.id not in planet_docking:
                    if DEBUG:
                        logger.debug("ship: {} docking to planet: {}"
                                     .format(ship.id, planet.id))
                    command_queue.append(ship.dock(planet))
                    planet_docking.append(planet.id)
                elif DEBUG:
                    logger.debug("ship: {} waiting to dock to planet: {}"
                                 .format(ship.id, planet.id))
            else:
                planet = None
                if (ship.id % 3) < 2:
                    # find ship's closest planet to navigate to
                    planet = find_closest_unowned_planet(game_map, ship, unowned_planets)
                elif len(unowned_planets) > 0:
                    planet = unowned_planets[0]
                if planet:
                    if DEBUG:
                        logger.debug("ship: {} off to planet: {}"
                                     .format(ship.id, planet.id))
                    navigate_command = ship.navigate(ship.closest_point_to(planet),
                                                     game_map, speed=ship_speed, ignore_ships=ignore_ships)
                    if navigate_command:
                        command_queue.append(navigate_command)
                else:
                    # no unowned planets, go looking for trouble
                    if len(docked_enemy_ships) > 1:
                        target_ship = docked_enemy_ships[ship.id % len(docked_enemy_ships)]
                    elif len(enemy_ships) > 1:
                        target_ship = enemy_ships[ship.id % len(enemy_ships)]
                    else:
                        target_ship = enemy_ships[0]
                    if target_ship:
                        if DEBUG:
                            logger.debug("ship: {} no planets so off to ship: {}"
                                         .format(ship.id, target_ship.id))
                        navigate_command = ship.navigate(ship.closest_point_to(target_ship),
                                                         game_map, speed=ship_speed,
                                                         ignore_ships=True)
                        if navigate_command:
                            command_queue.append(navigate_command)
                    else:
                        if DEBUG:
                            logger.debug("ship: {} no work".format(ship.id))
    
        # Send our set of commands to the Halite engine for this turn
        turn_end_presend = time.time()
        logger.info("turn: {} end ships time: {:.03f}"
                         .format(turn, turn_end_presend - turn_start_us))
        game.send_command_queue(command_queue)
        logger.info("turn: {} send_command_queue len: {} took: {:.03f}"
                         .format(turn, len(command_queue), time.time() - turn_end_presend))
        # TURN END
    # GAME END

if __name__ == "__main__":
        halite2_main()
