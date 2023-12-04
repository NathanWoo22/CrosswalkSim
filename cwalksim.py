import os 
import math
import random as rand
import queue
import heapq
from enum import Enum

class ShortFile(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return(repr(self.value))

class WelfordStatistics:
    def __init__(self) -> None:
        self.x_bar = 0
        self.vi = 0
        self.i = 0
    
    def add_data_point(self, x_i:float) -> None:
        self.i += 1
        self.vi = self.vi + (self.i - 1) / self.i * (x_i - self.x_bar)**2
        self.x_bar = self.x_bar + (x_i - self.x_bar)/self.i
    
    def get_average(self):
        return self.x_bar
    
    def get_sd(self):
        return math.sqrt(self.vi/self.i)

    def get_n(self):
        return self.i
    
class State(Enum):
    GREEN_PRESSED = 1
    GREEN_TIMER_EXPIRED = 2
    GREEN_TIMER_COUNTING = 3
    YELLOW = 4
    RED = 5

class EventType(Enum):
    AUTO_ARRIVAL = 1
    PED_ARRIVAL = 2
    PED_AT_BUTTON = 3
    PED_IMPATIENT = 4
    GREEN_EXPIRES = 5
    YELLOW_EXPIRES = 6
    RED_EXPIRES = 7
    AUTO_EXIT = 8
    PED_EXIT = 9

class Event: 
    def __init__(self, at, event_type, ped) -> None:
        self.at = at
        self.event_type = event_type
        self.ped = ped
        
class PriorityQueue:
    def __init__(self):
        self.queue = []
        self.index = 0  # Used to maintain the order of elements with equal priority

    def push(self, item, priority):
        heapq.heappush(self.queue, (priority, self.index, item))
        self.index += 1

    def pop(self):
        return heapq.heappop(self.queue)[-1]
    
    def length(self):
        return len(self.queue)
    
class Ped:
    def __init__(self, speed, entryTime):
        self.speed = speed
        self.entryTime = entryTime

class Auto:
    def __init__(self, speed, entryTime, delay):
        self.speed = speed
        self.entryTime = entryTime
        self.delay = delay

priority_queue = PriorityQueue()
state = State.GREEN_TIMER_EXPIRED
t = 0
green_timer = 0

def walk_request_pushed():
    global state
    global priority_queue
    global t
    global green_timer
    if state == State.GREEN_TIMER_EXPIRED:
        nextEvent = Event(t, EventType.GREEN_EXPIRES, None)
        priority_queue.push(nextEvent, nextEvent.at)
    elif state == State.GREEN_TIMER_COUNTING:
        nextEvent = Event(green_timer, EventType.GREEN_EXPIRES, None)
        priority_queue.push(nextEvent, nextEvent.at)
        state = State.GREEN_PRESSED
    elif state == State.GREEN_PRESSED or state == State.YELLOW or state == State.RED:
        return

def sim(args):
    WIDTH_BLOCK = 330
    WIDTH_CROSSWALK = 24
    WIDTH_STREET = 46
    INITIAL_PED_TRAVEL_DIST = WIDTH_BLOCK + WIDTH_STREET
    RED = 18
    YELLOW = 8
    GREEN = 35
    LAMBDA_P = 6/60
    LAMBDA_A = 8/60
    AUTO_LENGTH = 9
    MIN_AUTO_SPEED = 2200/60
    MAX_AUTO_SPEED = 3080/60
    MIN_PED_SPEED = 2.6
    MAX_PED_SPEED = 4.1
    AUTO_ACCELERATION = 10
    CLOSE_EDGE = 3 * WIDTH_BLOCK + 3 * WIDTH_STREET + 0.5 * WIDTH_BLOCK - 0.5 * WIDTH_CROSSWALK
    FAR_EDGE = 3 * WIDTH_BLOCK + 3 * WIDTH_STREET + 0.5 * WIDTH_BLOCK + 0.5 * WIDTH_CROSSWALK

    ped_count = 0
    auto_count = 0 
    
    button_pushed = False
    time_to_switch = 0 
    waiting_peds = []
    autos = []
    peds_crossed = 0
    ws = WelfordStatistics()
    ws2 = WelfordStatistics()
    
    global N
    global priority_queue
    global state
    global t
    global green_timer
    global ped_random
    global button_random
    global auto_random

    priority_queue.push(Event(0, EventType.PED_ARRIVAL, None), t)
    priority_queue.push(Event(0, EventType.AUTO_ARRIVAL, None), t)
    ped_count += 1

    while priority_queue.length() > 0:
        
        event = priority_queue.pop()
        t = event.at
        eventType = event.event_type
        # Create new pedestrian
        if eventType == EventType.PED_ARRIVAL:
            try:
                ped = Ped(float(next(ped_random)) * float((MAX_PED_SPEED - MIN_PED_SPEED)) + float(MIN_PED_SPEED), t)
            except Exception as e:
                print("Cannot read next uniform")
                exit(7)
            nextEvent = Event(t + INITIAL_PED_TRAVEL_DIST / ped.speed, EventType.PED_AT_BUTTON, ped)
            priority_queue.push(nextEvent, nextEvent.at)

            if ped_count < N:
                nextEvent = Event(t + - (1/LAMBDA_P * math.log(1 - float(next(ped_random)))), EventType.PED_ARRIVAL, None)
                priority_queue.push(nextEvent, nextEvent.at)

                ped_count += 1

        if eventType == EventType.AUTO_ARRIVAL:
            try:
                auto = Auto(float(next(auto_random)) * float((MAX_AUTO_SPEED - MIN_AUTO_SPEED)) + float(MIN_AUTO_SPEED), t, None)
            except Exception as e:
                print("Cannot read next uniform")
                exit(7)
            autos.append(auto)
            
            if auto_count < N:
                nextEvent = Event(t + -(1/LAMBDA_A * math.log(1-float(next(auto_random)))), EventType.AUTO_ARRIVAL, None)
                priority_queue.push(nextEvent, nextEvent.at)
                auto_count += 1


        if eventType == EventType.PED_AT_BUTTON:
            ped = event.ped

            # Check that the pedestrian can cross the street immediately
            time_to_cross = WIDTH_STREET / ped.speed
            if state == State.RED:
                if t + time_to_cross < time_to_switch and peds_crossed < 20:
                    # If we are here then we are good to cross 
                    nextEvent = Event(t + time_to_cross, EventType.PED_EXIT, ped)
                    priority_queue.push(nextEvent, nextEvent.at)
                    peds_crossed += 1
                else:
                    waiting_peds.append(ped)
                    nextEvent = Event(time_to_switch + 60, EventType.PED_IMPATIENT, ped)
                    priority_queue.push(nextEvent, nextEvent.at)

            # Nope not good to cross
            else:
                try:
                    chance = float(next(button_random))
                except Exception as e:
                    print("Cannot read next uniform")
                    exit(7)
                if len(waiting_peds) == 0:
                    if chance < 15/16:
                        walk_request_pushed()
                else: 
                    if chance > 1/(1 + len(waiting_peds)):
                        walk_request_pushed()
                waiting_peds.append(ped)
                nextEvent = Event(t + 60, EventType.PED_IMPATIENT, ped)
                priority_queue.push(nextEvent, nextEvent.at)
                        
        if eventType == EventType.PED_IMPATIENT:
            walk_request_pushed()
        
        if eventType == EventType.PED_EXIT:
            ped = event.ped
            expectedTime = (INITIAL_PED_TRAVEL_DIST + WIDTH_STREET) / ped.speed
            actualTime = t - ped.entryTime 
            ws.add_data_point((actualTime - expectedTime))

        if eventType == EventType.AUTO_EXIT:
            auto = event.ped
            expectedTime = (7 * WIDTH_BLOCK + 6 * WIDTH_STREET) / auto.speed
            actualTime = auto.delay
            # print(expectedTime)
            print(actualTime-expectedTime)
            ws2.add_data_point(actualTime - expectedTime)

        if eventType == EventType.GREEN_EXPIRES:
            state = State.YELLOW
            nextEvent = Event(t + YELLOW, EventType.YELLOW_EXPIRES, None)
            priority_queue.push(nextEvent, nextEvent.at)
            state = State.YELLOW

            for auto in autos:
                delay = 0 
                if (t + YELLOW - auto.entryTime) * auto.speed > FAR_EDGE + 9 or (t + YELLOW + RED - auto.entryTime) * auto.speed < CLOSE_EDGE: 
                    delay = (7 * WIDTH_BLOCK + 6 * WIDTH_STREET) / auto.speed
                else:
                    bj = auto.speed ** 2 / (2 * AUTO_ACCELERATION)
                    tj = auto.speed / AUTO_ACCELERATION
                    delay1 = (7 * WIDTH_BLOCK + 6 * WIDTH_STREET - 2 * bj) / auto.speed 
                    delay2 = 2 * tj
                    hj = auto.entryTime + (7 * WIDTH_BLOCK + 6 * WIDTH_STREET - WIDTH_CROSSWALK - 2 * bj) / (2 * auto.speed) + tj
                    delay3 = t + YELLOW + RED - hj
                    delay = delay1 + delay2 + delay3
                auto.delay = delay
                nextEvent = Event(t, EventType.AUTO_EXIT, auto)
                priority_queue.push(nextEvent, nextEvent.at)
            autos = []


        if eventType == EventType.YELLOW_EXPIRES:
            time_to_switch = t + RED
            while peds_crossed < 20 and len(waiting_peds) > 0:
                ped = waiting_peds.pop(0)
                time_to_cross = WIDTH_STREET / ped.speed
                nextEvent = Event(t + time_to_cross, EventType.PED_EXIT, ped)
                priority_queue.push(nextEvent, nextEvent.at)
                peds_crossed += 1
            nextEvent = Event(t + RED, EventType.RED_EXPIRES, None)
            priority_queue.push(nextEvent, nextEvent.at)
            state = State.RED

        if eventType == EventType.RED_EXPIRES:
            green_timer = t + GREEN
            state = State.GREEN_TIMER_COUNTING
            peds_crossed = 0 


    print("OUTPUT " + str(ws2.get_average()) + " " + str(ws2.get_sd()**2) + " " + str(ws.get_average()))
    # print(ws.get_average())
    # print(ws.get_sd())

randomNumbers = []
def main(args):
    # print(len(args))
    if len(args) != 5:
        print("Usage is ./SIM <pedestrians> <Uniform samples> <Uniform samples> <Uniform samples>")
        exit(1)

    global N
    global auto_random
    global ped_random
    global button_random
    try:
        N = int(args[1])
        auto_random = open(args[2], "r")
        ped_random = open(args[3], "r")
        button_random = open(args[4], "r")
        sim(args)
            
    except FileNotFoundError:
        print(f"The file {args[2]} does not exist")
        exit(5)
    except PermissionError:
        print(f"No permission on {args[2]}")
        exit(6)
    except Exception as e:
        print(f"An rando error {str(e)}")
        exit(7)











    

    
