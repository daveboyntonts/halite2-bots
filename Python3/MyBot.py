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

from random import sample, randint

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

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
game = hlt.Game("Settler 0.6")

#persist between turns
planet_target = {}

while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    
    game_map = game.update_map()

    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    #only 1 ship can dock per turn?
    unowned_planets = [p for p in game_map.all_planets() if not p.is_owned()]
    planet_docking = []

    ship_speed = hlt.constants.MAX_SPEED*0.8
    ship_action_limit = 70
    ship_actions = 0

    # For every ship that I control
    all_ships = game_map.get_me().all_ships()
    if len(all_ships) > 50:
        ignore_ships = True
    else:
        ignore_ships = False

    # sample/shuffle ships to avoid deadlocks
    for ship in sample(all_ships, len(all_ships)):
        # If the ship is undocked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            continue

        # limit the non-trivial number of ships we look at per turn
        ship_actions += 1
        if ship_actions > ship_action_limit:
            break

        # if there are still unowned planets
        if len(unowned_planets) > 0:
            # For each unowned planet in the game (only non-destroyed planets are included)
            for planet in unowned_planets:
                # allow only 1 docking at a time, otherwise will wait until full
                if ship.can_dock(planet):
                    if planet.id not in planet_docking:
                        command_queue.append(ship.dock(planet))
                        planet_docking.append(planet.id)
                        break
                else:
                    # If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
                    # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
                    # We run this navigate command each turn until we arrive to get the latest move.
                    # Here we move at half our maximum speed to better control the ships
                    # In order to execute faster we also choose to ignore ship collision calculations during navigation.
                    # This will mean that you have a higher probability of crashing into ships, but it also means you will
                    # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
                    # wish to turn that option off.
                    navigate_command = ship.navigate(ship.closest_point_to(planet),
                                                     game_map, speed=ship_speed, ignore_ships=ignore_ships)
                    if navigate_command:
                        command_queue.append(navigate_command)
                        break
        else:
            # no unowned planets, go looking for trouble
            target_ship = closest_enemy(game_map, ship)
            if target_ship:
                navigate_command = ship.navigate(ship.closest_point_to(target_ship),
                                                 game_map, speed=ship_speed,
                                                 ignore_ships=ignore_ships)
                if navigate_command:
                    command_queue.append(navigate_command)

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
