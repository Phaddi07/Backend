import pygame # type: ignore
import numpy as np # type: ignore
import csv
import random
import heapq

# ---------------- CONFIG ----------------
GRID_WIDTH = 20
GRID_HEIGHT = 20
CELL_SIZE = 30

# Simulation parameters
N_TAXIS = 10  # number of taxis
TARGET_FPS = 30
SIMULATION_TICKS_PER_SECOND = 2

DEMAND_REDUCTION_RATE_PER_SECOND = 30
DEMAND_REDUCTION_PER_TICK = DEMAND_REDUCTION_RATE_PER_SECOND / SIMULATION_TICKS_PER_SECOND
FRAMES_PER_TICK = max(1, int(TARGET_FPS / SIMULATION_TICKS_PER_SECOND))

# Initialize demand maps
demand_map = np.zeros((GRID_WIDTH, GRID_HEIGHT))
demand_history_map = np.zeros((GRID_WIDTH, GRID_HEIGHT))
click_events = []

# ---------------- ROADS & CITY LAYOUT ----------------
roads = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=bool)

# Horizontal & vertical main roads
horizontal_roads = [3, 6, 9, 12, 15, 18]
vertical_roads = [3, 6, 9, 12, 15, 18]
for y in horizontal_roads:
    roads[:, y] = True
for x in vertical_roads:
    roads[x, :] = True

# ---------------- TAXI CLASS ----------------
class Taxi:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.display_x = x
        self.display_y = y
        self.trail = []
        self.destination = (x, y)
        self.state = "IDLE"
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
                self.path = []

    def move(self):
        if self.state in ["EN_ROUTE", "DROPPING_OFF", "ROAMING"] and self.path:
            next_pos = self.path.pop(0)
            self.x, self.y = next_pos
            self.trail.append((self.x, self.y))
            if len(self.trail) > 2:
                self.trail.pop(0)

    def update_display_position(self, alpha=0.2):
        self.display_x += (self.x - self.display_x) * alpha
        self.display_y += (self.y - self.display_y) * alpha

# ---------------- PATHFINDING ----------------
def find_path(start_pos, end_pos):
    """A* pathfinding restricted to roads."""
    def heuristic(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

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

        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            neighbor = (current[0]+dx, current[1]+dy)
            if not (0 <= neighbor[0] < GRID_WIDTH and 0 <= neighbor[1] < GRID_HEIGHT):
                continue
            if not roads[neighbor]:
                continue  # only move on roads
            tentative_g_score = g_score[current]+1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                g_score[neighbor] = tentative_g_score
                f_score = tentative_g_score + heuristic(neighbor, end_pos)
                heapq.heappush(open_list, (f_score, neighbor))
                came_from[neighbor] = current
    return []

# ---------------- DEMAND LOGIC ----------------
def update_demand(time_tick, serviced_tiles):
    for ce in click_events[:]:
        if ce["ticks"] < ce["duration"]:
            if (ce["x"], ce["y"]) not in serviced_tiles:
                demand_map[ce["x"], ce["y"]] += ce["intensity"]
            ce["ticks"] += 1
        else:
            click_events.remove(ce)

def assign_unique_targets():
    demand_cells = [((x,y), demand_map[x][y]) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)]
    demand_cells.sort(key=lambda item: -item[1])
    assigned_destinations = set(t.destination for t in taxis if t.state!="IDLE")
    assignments = []

    for taxi in [t for t in taxis if t.state=="IDLE"]:
        potential_targets = [(pos,val) for pos,val in demand_cells if val>0 and pos not in assigned_destinations and pos!=taxi.last_serviced_tile]
        if potential_targets:
            (x,y), _ = potential_targets[0]
            assignments.append(((x,y), taxi, "EN_ROUTE"))
            assigned_destinations.add((x,y))
        else:
            while True:
                rx, ry = np.random.randint(0,GRID_WIDTH), np.random.randint(0,GRID_HEIGHT)
                if roads[rx, ry] and (rx, ry) not in assigned_destinations:
                    assignments.append(((rx,ry), taxi, "ROAMING"))
                    assigned_destinations.add((rx,ry))
                    break
    return assignments

# ---------------- INITIALIZE TAXIS ----------------
taxis = []
road_positions = [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT) if roads[x,y]]
for _ in range(N_TAXIS):
    x, y = random.choice(road_positions)
    taxis.append(Taxi(x, y))

# ---------------- CSV LOG ----------------
csv_file = open("taxi_swarm_log.csv", "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["time","taxi_id","x","y"])

# ---------------- SIMULATION STEP ----------------
def step_simulation(time_tick):
    serviced_tiles = set((t.x, t.y) for t in taxis if t.state=="SERVICING")
    update_demand(time_tick, serviced_tiles)

    for idx, taxi in enumerate(taxis):
        taxi.move()
        if not taxi.path:
            if taxi.state=="EN_ROUTE":
                taxi.state="SERVICING"
            elif taxi.state in ["DROPPING_OFF","ROAMING"]:
                taxi.state="IDLE"

        if taxi.state=="SERVICING":
            if demand_map[taxi.x,taxi.y]>0:
                demand_map[taxi.x,taxi.y]=max(0,demand_map[taxi.x,taxi.y]-DEMAND_REDUCTION_PER_TICK)
            else:
                demand_history_map[taxi.x,taxi.y]+=1
                taxi.last_serviced_tile=(taxi.x,taxi.y)
                drop_x, drop_y = random.choice(road_positions)
                taxi.set_destination(drop_x, drop_y)
                taxi.state="DROPPING_OFF" if taxi.path else "IDLE"

        csv_writer.writerow([time_tick, idx, taxi.x, taxi.y])

    assignments = assign_unique_targets()
    for (tx,ty), taxi, new_state in assignments:
        taxi.set_destination(tx,ty)
        taxi.state = new_state if taxi.path else "IDLE"

# ---------------- PYGAME VISUALS ----------------
pygame.init()
screen = pygame.display.set_mode((GRID_WIDTH*CELL_SIZE, GRID_HEIGHT*CELL_SIZE+40))
pygame.display.set_caption("Taxi Swarm Simulation")
font = pygame.font.SysFont("Consolas", 12)
clock = pygame.time.Clock()

# ---------------- DEMAND VISUALS ----------------
def draw_demand_zones():
    for ce in click_events:
        intensity_color = min(255, int(ce["intensity"]*10))
        rect = pygame.Rect(ce["x"]*CELL_SIZE, ce["y"]*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, (255, 50, 50, intensity_color), rect)

# ---------------- GRID & TAXI VISUALS ----------------
def draw_grid():
    drop_off_points = {t.destination for t in taxis if t.state=="DROPPING_OFF"}
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            rect = pygame.Rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if (x,y) in drop_off_points:
                color=(0,200,0)
            elif roads[x,y]:
                color=(50,50,50)
            else:
                color=(30,30,30)
            pygame.draw.rect(screen,color,rect)
            pygame.draw.rect(screen,(80,80,80),rect,1)

def draw_taxis():
    for taxi in taxis:
        taxi.update_display_position()
        for t in range(1,len(taxi.trail)):
            p1=taxi.trail[t-1]; p2=taxi.trail[t]
            pygame.draw.line(screen,(180,180,0),
                             (p1[0]*CELL_SIZE+CELL_SIZE//2,p1[1]*CELL_SIZE+CELL_SIZE//2),
                             (p2[0]*CELL_SIZE+CELL_SIZE//2,p2[1]*CELL_SIZE+CELL_SIZE//2),2)
        rect = pygame.Rect(taxi.display_x*CELL_SIZE+6, taxi.display_y*CELL_SIZE+6,
                           CELL_SIZE-12, CELL_SIZE-12)
        color=(255,255,0) if taxi.state=="SERVICING" else (0,150,255) if taxi.state=="DROPPING_OFF" else (200,200,200)
        pygame.draw.rect(screen,color,rect,border_radius=4)
        pygame.draw.rect(screen,(0,0,0),rect,1,border_radius=4)

def draw_labels(time_tick):
    label = font.render(f"Time: {time_tick}", True,(255,255,255))
    screen.blit(label,(10,GRID_HEIGHT*CELL_SIZE+10))

# ---------------- RUN SIMULATION ----------------
def run_simulation():
    time_tick=0
    frame_counter=0
    running=True

    demand_intensity_setting = 15
    demand_duration_setting = 20

    while running:
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False
            elif event.type==pygame.MOUSEBUTTONDOWN:
                mx,my=pygame.mouse.get_pos()
                gx,gy=mx//CELL_SIZE,my//CELL_SIZE
                if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT and roads[gx,gy]:
                    if event.button == 1:  # left click to add demand
                        click_events.append({"x":gx,"y":gy,"intensity":demand_intensity_setting,
                                             "duration":demand_duration_setting,"ticks":0})
                    elif event.button == 3:  # right click to remove demand
                        click_events[:] = [ce for ce in click_events if not (ce["x"]==gx and ce["y"]==gy)]
            elif event.type==pygame.KEYDOWN:
                if event.unicode.isdigit() and event.unicode != "0":
                    demand_intensity_setting = int(event.unicode) * 5
                elif event.key == pygame.K_LEFTBRACKET:
                    demand_duration_setting = max(1, demand_duration_setting - 5)
                elif event.key == pygame.K_RIGHTBRACKET:
                    demand_duration_setting += 5

        frame_counter +=1
        if frame_counter >= FRAMES_PER_TICK:
            frame_counter=0
            step_simulation(time_tick)
            time_tick+=1

        screen.fill((30,30,30))
        draw_grid()
        draw_demand_zones()
        draw_taxis()
        draw_labels(time_tick)
        pygame.display.flip()
        clock.tick(TARGET_FPS)

    csv_file.close()
    pygame.quit()

# ---------------- ENTRY POINT ----------------
if __name__=="__main__":
    run_simulation()

