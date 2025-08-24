import pygame
import numpy as np
import csv
import random
import heapq

# Grid setup
GRID_WIDTH = 20
GRID_HEIGHT = 20
CELL_SIZE = 30

# Initialize demand and history maps
demand_map = np.zeros((GRID_WIDTH, GRID_HEIGHT))
demand_history_map = np.zeros((GRID_WIDTH, GRID_HEIGHT))

# Taxi class
class Taxi:
    def _init_(self, x, y):
        self.x = x
        self.y = y
        self.display_x = x
        self.display_y = y
        self.trail = []
        self.destination = (x, y)
        self.state = "IDLE"  # Can be "IDLE", "EN_ROUTE", "SERVICING", "DROPPING_OFF", "ROAMING"
        self.path = []
        self.last_serviced_tile = None

    def set_destination(self, target_x, target_y):
        self.destination = (target_x, target_y)
        if (self.x, self.y) == self.destination:
            self.path = []
        else:
            self.path = find_path((self.x, self.y), self.destination)
            if self.path and len(self.path) > 1:
                self.path.pop(0)
            else:
                self.path = [] # No path found

    def move(self):
        # Taxis move if they are en route to demand or a dropoff point
        if self.state in ["EN_ROUTE", "DROPPING_OFF", "ROAMING"] and self.path:
            next_pos = self.path.pop(0)
            self.x, self.y = next_pos
            self.trail.append((self.x, self.y))
            if len(self.trail) > 30:
                self.trail.pop(0)

    def update_display_position(self, alpha=0.2):
        self.display_x += (self.x - self.display_x) * alpha
        self.display_y += (self.y - self.display_y) * alpha

def find_path(start_pos, end_pos):
    """A* pathfinding algorithm."""
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_list = []
    heapq.heappush(open_list, (0, start_pos))
    came_from = {}
    g_score = {start_pos: 0}

    while open_list:
        _, current = heapq.heappop(open_list)

        if current == end_pos:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start_pos)
            return path[::-1]

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if not (0 <= neighbor[0] < GRID_WIDTH and 0 <= neighbor[1] < GRID_HEIGHT):
                continue

            tentative_g_score = g_score[current] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                g_score[neighbor] = tentative_g_score
                f_score = tentative_g_score + heuristic(neighbor, end_pos)
                heapq.heappush(open_list, (f_score, neighbor))
                came_from[neighbor] = current
    return None # No path found

# Predefined event zones
event_zones = [
    {"x_range": range(14, 17), "y_range": range(14, 17), "intensity": 15, "duration": 30},
    {"x_range": range(4, 7), "y_range": range(10, 13), "intensity": 12, "duration": 25},
]
event_counters = [0] * len(event_zones)
click_events = []

# Drop-off points are now fully random, so no predefined zones are needed.

# Update demand map
def update_demand(time_tick, serviced_tiles):
    # demand_map[:, :] = np.random.randint(0, 3, (GRID_WIDTH, GRID_HEIGHT)) # This was causing the issue
    for idx, event in enumerate(event_zones):
        if event_counters[idx] < event["duration"]:
            for x in event["x_range"]:
                for y in event["y_range"]:
                    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT and (x, y) not in serviced_tiles:
                        demand_map[x][y] += event["intensity"]
            event_counters[idx] += 1
    for ce in click_events[:]:
        if ce["ticks"] < ce["duration"]:
            if (ce["x"], ce["y"]) not in serviced_tiles:
                demand_map[ce["x"], ce["y"]] += ce["intensity"]
            ce["ticks"] += 1
        else:
            click_events.remove(ce)

# Assign unique targets to each taxi
def assign_unique_targets():
    demand_cells = [((x, y), demand_map[x][y]) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)]
    demand_cells.sort(key=lambda item: -item[1])

    assigned_destinations = set(t.destination for t in taxis if t.state != "IDLE")
    assignments = []
    
    for taxi in [t for t in taxis if t.state == "IDLE"]:
        potential_targets = [(pos, val) for pos, val in demand_cells if val > 0 and pos not in assigned_destinations and pos != taxi.last_serviced_tile]
        
        if potential_targets:
            (x, y), _ = potential_targets[0]
            assignments.append(((x, y), taxi, "EN_ROUTE"))
            assigned_destinations.add((x, y))
        else:
            historical_cells = [((x, y), demand_history_map[x][y]) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)]
            historical_cells.sort(key=lambda item: -item[1])
            
            roaming_target = None
            for pos, val in historical_cells:
                if pos not in assigned_destinations and pos != (taxi.x, taxi.y):
                    roaming_target = pos
                    break
            
            if roaming_target:
                assignments.append((roaming_target, taxi, "ROAMING"))
                assigned_destinations.add(roaming_target)
            else:
                # Fallback to random if no other option
                while True:
                    rx, ry = np.random.randint(0, GRID_WIDTH), np.random.randint(0, GRID_HEIGHT)
                    if (rx, ry) not in assigned_destinations:
                        assignments.append(((rx, ry), taxi, "ROAMING"))
                        assigned_destinations.add((rx, ry))
                        break
    return assignments

# Taxi fleet
taxis = [Taxi(np.random.randint(0, GRID_WIDTH), np.random.randint(0, GRID_HEIGHT)) for _ in range(20)]

# CSV logging
csv_file = open("taxi_swarm_log.csv", "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["time", "taxi_id", "x", "y"])

# Simulation step
def step_simulation(time_tick):
    # Update demand map first
    serviced_tiles = set((t.x, t.y) for t in taxis if t.state == "SERVICING")
    update_demand(time_tick, serviced_tiles)

    # Process taxi movement and state changes
    for idx, taxi in enumerate(taxis):
        # 1. Move the taxi
        taxi.move()

        # 2. Check for arrival and update state
        if not taxi.path:
            if taxi.state == "EN_ROUTE":
                taxi.state = "SERVICING"
            elif taxi.state == "DROPPING_OFF" or taxi.state == "ROAMING":
                taxi.state = "IDLE"

        # 3. Handle actions for the current state
        if taxi.state == "SERVICING":
            if demand_map[taxi.x, taxi.y] > 0:
                demand_map[taxi.x, taxi.y] = max(0, demand_map[taxi.x, taxi.y] - DEMAND_REDUCTION_PER_TICK)
            else:
                # Demand is met, transition to drop-off
                demand_history_map[taxi.x, taxi.y] += 1
                taxi.last_serviced_tile = (taxi.x, taxi.y)
                
                # Assign a completely random drop-off point on the grid
                drop_x = np.random.randint(0, GRID_WIDTH)
                drop_y = np.random.randint(0, GRID_HEIGHT)
                
                taxi.set_destination(drop_x, drop_y)
                taxi.state = "DROPPING_OFF" if taxi.path else "IDLE"
        
        csv_writer.writerow([time_tick, idx, taxi.x, taxi.y])

    # 4. Assign new tasks to idle taxis
    assignments = assign_unique_targets()
    for (tx, ty), taxi, new_state in assignments:
        taxi.set_destination(tx, ty)
        taxi.state = new_state if taxi.path else "IDLE"

# Pygame visuals
pygame.init()
screen = pygame.display.set_mode((GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE + 40))
pygame.display.set_caption("Taxi Swarm with Gradual Demand Servicing")
font = pygame.font.SysFont("Consolas", 12)

# Simulation timing
TARGET_FPS = 30
SIMULATION_TICKS_PER_SECOND = 2
DEMAND_REDUCTION_RATE_PER_SECOND = 30  # Increased for faster demand reduction
DEMAND_REDUCTION_PER_TICK = DEMAND_REDUCTION_RATE_PER_SECOND / SIMULATION_TICKS_PER_SECOND
FRAMES_PER_TICK = max(1, int(TARGET_FPS / SIMULATION_TICKS_PER_SECOND))

def draw_grid():
    drop_off_points = {t.destination for t in taxis if t.state == "DROPPING_OFF"}
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if (x, y) in drop_off_points:
                color = (0, 200, 0)  # Green for drop-off points
                pygame.draw.rect(screen, color, rect)
            else:
                value = min(demand_map[x][y], 10)
                color = (255, int(255 - value * 25), int(255 - value * 25))
                pygame.draw.rect(screen, color, rect)
                label = font.render(str(int(demand_map[x][y])), True, (0, 0, 0))
                screen.blit(label, (x * CELL_SIZE + 6, y * CELL_SIZE + 4))
            pygame.draw.rect(screen, (50, 50, 50), rect, 1)

def draw_taxis():
    for taxi in taxis:
        taxi.update_display_position()
        for t in range(1, len(taxi.trail)):
            p1 = taxi.trail[t - 1]
            p2 = taxi.trail[t]
            pygame.draw.line(screen, (180, 180, 0),
                (p1[0] * CELL_SIZE + CELL_SIZE // 2, p1[1] * CELL_SIZE + CELL_SIZE // 2),
                (p2[0] * CELL_SIZE + CELL_SIZE // 2, p2[1] * CELL_SIZE + CELL_SIZE // 2), 2)
        pygame.draw.circle(screen, (0, 0, 0),
            (taxi.destination[0] * CELL_SIZE + CELL_SIZE // 2,
             taxi.destination[1] * CELL_SIZE + CELL_SIZE // 2), 4)
        rect = pygame.Rect(taxi.display_x * CELL_SIZE + 6, taxi.display_y * CELL_SIZE + 6,
                           CELL_SIZE - 12, CELL_SIZE - 12)
        # Change color if taxi is dropping someone off
        if taxi.state == "DROPPING_OFF":
            color = (0, 150, 255)
        elif taxi.state == "ROAMING":
            color = (200, 200, 200)  # Grey for roaming
        else:
            color = (255, 255, 0) # Yellow for standard
        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, (0, 0, 0), rect, 1, border_radius=4)

def draw_labels(time_tick):
    label = font.render(f"Time: {time_tick}", True, (255, 255, 255))
    screen.blit(label, (10, GRID_HEIGHT * CELL_SIZE + 10))

def run_simulation():
    clock = pygame.time.Clock()
    time_tick = 0
    frame_counter = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                gx = mx // CELL_SIZE
                gy = my // CELL_SIZE
                if gx < GRID_WIDTH and gy < GRID_HEIGHT:
                    click_events.append({"x": gx, "y": gy, "intensity": 15, "duration": 20, "ticks": 0})
            elif event.type == pygame.WINDOWCLOSE:
                running = False

        # Update simulation state at a fixed rate
        frame_counter += 1
        if frame_counter >= FRAMES_PER_TICK:
            frame_counter = 0
            step_simulation(time_tick)
            time_tick += 1

        # Drawing
        screen.fill((30, 30, 30))
        draw_grid()
        draw_taxis()
        draw_labels(time_tick)
        pygame.display.flip()

        clock.tick(TARGET_FPS)

    csv_file.close()
    pygame.quit()

# Start simulation
if _name_ == "_main_":
    run_simulation()