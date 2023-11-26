import os 
import math
import random as rand
import queue
import heapq
from enum import Enum

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

def main(args):
    N = 400
    WIDTH_BLOCK = 330
    WIDTH_CROSSWALK = 24
    WIDTH_STREET = 46
    INITIAL_PED_TRAVEL_DIST = WIDTH_BLOCK + WIDTH_STREET
    RED = 18
    YELLOW = 8
    GREEN = 35
    LAMBDA_P = 6/60
    LAMBDA_A = 4/60
    AUTO_LENGTH = 9
    MIN_AUTO_SPEED = 2200/60
    MAX_AUTO_SPEED = 3080/60
    MIN_PED_SPEED = 2.6
    MAX_PED_SPEED = 4.1
    AUTO_ACCELERATION = 10

    ped_count = 0
    auto_count = 0 
    
    button_pushed = False
    time_to_switch = 0 
    waiting_peds = []
    peds_crossed = 0
    ws = WelfordStatistics()
    
    global priority_queue
    global state
    global t
    global green_timer

    priority_queue.push(Event(0, EventType.PED_ARRIVAL, None), t)
    ped_count += 1

    while priority_queue.length() > 0:
        
        event = priority_queue.pop()
        t = event.at
        eventType = event.event_type
        # Create new pedestrian
        if eventType == EventType.PED_ARRIVAL:
            ped = Ped(rand.uniform(MIN_PED_SPEED, MAX_PED_SPEED), t)
            nextEvent = Event(t + INITIAL_PED_TRAVEL_DIST / ped.speed, EventType.PED_AT_BUTTON, ped)
            priority_queue.push(nextEvent, nextEvent.at)

            if ped_count < 400:
                nextEvent = Event(t + rand.expovariate(LAMBDA_P), EventType.PED_ARRIVAL, None)
                priority_queue.push(nextEvent, nextEvent.at)

                ped_count += 1

        if eventType == EventType.PED_AT_BUTTON:
            ped = event.ped

            # Check that the pedestrian can cross the street immediately
            time_to_cross = WIDTH_STREET / ped.speed
            if state == State.RED:
                if t + time_to_cross < time_to_switch and peds_crossed < 20:
                    # If we are here then we are good to cross 
                    nextEvent = Event(t + time_to_cross, EventType.PED_EXIT, ped)
                    priority_queue.push(nextEvent, nextEvent.at)
                else:
                    waiting_peds.append(ped)
                    nextEvent = Event(time_to_switch + 60, EventType.PED_IMPATIENT, ped)
                    priority_queue.push(nextEvent, nextEvent.at)

            # Nope not good to cross
            else:
                chance = float(rand.random())
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
            expectedTime = (WIDTH_BLOCK + 2 * WIDTH_STREET) / ped.speed 
            actualTime = t - ped.entryTime 
            ws.add_data_point(actualTime - expectedTime)

        if eventType == EventType.GREEN_EXPIRES:
            state = State.YELLOW
            nextEvent = Event(t + YELLOW, EventType.YELLOW_EXPIRES, None)
            priority_queue.push(nextEvent, nextEvent.at)
            state = State.YELLOW

        if eventType == EventType.YELLOW_EXPIRES:
            time_to_switch = t + GREEN
            while peds_crossed < 20 and len(waiting_peds) > 0:
                ped = waiting_peds.pop()
                time_to_cross = WIDTH_STREET / ped.speed
                nextEvent = Event(t + time_to_cross, EventType.PED_EXIT, ped)
                priority_queue.push(nextEvent, nextEvent.at)
                peds_crossed += 1
            nextEvent = Event(t + RED, EventType.RED_EXPIRES, None)
            priority_queue.push(nextEvent, nextEvent.at)
            state = State.RED

        if eventType == EventType.RED_EXPIRES:
            green_timer = t + 60
            state = State.GREEN_TIMER_COUNTING
            peds_crossed = 0 


    print("OUTPUT " + str(ws.get_average()) + " " + str(ws.get_average()) + " " + str(ws.get_average()))
    # print(ws.get_average())
    # print(ws.get_sd())










    

    
