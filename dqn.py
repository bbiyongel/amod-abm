import time
import csv
import copy
import pandas as pd
import argparse
import numpy as np
import random
import datetime
from multiprocessing import *
import mplleaflet
import matplotlib.pyplot as plt
from collections import deque
from matplotlib import animation
import matplotlib.image as mpimg

from lib.OsrmEngine import *
from lib.Agents import *
from lib.Demand import *
from lib.Constants import *
from lib.Env import *

FLEET_SIZE = 810
CAPACITY = 4

DEMAND_SCALER = 1600
DEMAND = BAL20
TOTAL_DEMAND = 1
DEMAND_STR = "BAL20"

def print_results(model, runtime, now):
    count_reqs = 0
    count_served = 0
    wt = 0.0
    vt = 0.0
    for req in model.reqs:
        if req.Tr >= WARM_UP and req.Tr <= WARM_UP+SIMULATION:
            count_reqs += 1
            if not np.isclose(req.Td, -1.0):
                count_served += 1
                wt += (req.Tp - req.Tr)
                vt += (req.Td - req.Tp)
    wt /= count_served
    vt /= count_served
    
    vstt = 0.0
    vsdt = 0.0
    vrtt = 0.0
    vrdt = 0.0
    for veh in model.vehs:
        vstt += veh.Ts
        vsdt += veh.Ds
        vrtt += veh.Tr
        vrdt += veh.Dr
    vstt /= model.V
    vsdt /= model.V
    vrtt /= model.V
    vrdt /= model.V

    print("*"*80)
    print("Scenario: %s; Simulated Annealing: %s; Rebalancing: %s" % (DEMAND_STR, SIMU_ANNEAL, REBALANCE))
    print("Simulation starts at %s" % (now))
    print("Runtime Time: %d s" % (runtime))
    print("System Settings:")
    print("  - Simulation Time: %d s" % SIMULATION)
    print("  - Fleet Size: %d; Capacity: %d" % (model.V, model.K))
    print("  - Demand Rate: %.1f trips/h" % (model.D))
    print("  - Assignment Interval: %.1f s" % ASSIGN_INT)
    print("  - Rebalancing Interval: %.1f s" % REBL_INT)
    print("Simulation Results:")
    print("  - Requests:")
    print("    + service rate: %.1f%% (%d/%d)" % (
        100.0*count_served/count_reqs, count_served, count_reqs))
    print("    + wait time: %.1f s" % (wt))
    print("    + in-vehicle time: %.1f s" % (vt))
    print("  - Vehicles:")
    print("    + vehicle service time travelled: %.1f s" % (vstt))
    print("    + vehicle service distance travelled: %.1f m" % (vsdt))
    print("    + vehicle service time percentage: %.1f%%" % (100.0*vstt/SIMULATION))
    print("    + vehicle rebalancing time travelled: %.1f s" % (vrtt))
    print("    + vehicle rebalancing distance travelled: %.1f m" % (vrdt))
    print("    + vehicle rebalancing time percentage: %.1f%%" % (100.0*vrtt/SIMULATION))
    print("*"*80)

    f = open('results.csv', 'a')
    writer = csv.writer(f)
    row = [DEMAND_STR, SIMU_ANNEAL, REBALANCE, SIMULATION, model.V, model.K, model.D, 100.0*count_served/count_reqs, count_served, count_reqs, wt, vt, vsdt, vstt, 100.0*vstt/SIMULATION, vrdt, vrtt, 100.0*vrtt/SIMULATION, None]
    writer.writerow(row)
    f.close()

    return [wt, vt, 100.0*vstt/SIMULATION, 100.0*vrtt/SIMULATION]

def anim(shots):
    def init():
        for i in range(len(vehs)):
            vehs[i].set_data([shots[0][i].lng], [shots[0][i].lat])
            r1x = []
            r1y = []
            r2x = []
            r2y = []
            r3x = []
            r3y = []
            count = 0
            for leg in shots[0][i].route:
                if leg.pod == 0:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r3x.extend(geo[0])
                        r3y.extend(geo[1])
                    assert len(shots[0][i].route) == 1
                    continue
                count += 1
                if count == 1:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r1x.extend(geo[0])
                        r1y.extend(geo[1])
                else:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r2x.extend(geo[0])
                        r2y.extend(geo[1])
            routes1[i].set_data( r1x, r1y )
            routes2[i].set_data( r2x, r2y )
            routes3[i].set_data( r3x, r3y )
        return vehs, routes1, routes2, routes3

    def animate(n):
        for i in range(len(vehs)):
            vehs[i].set_data([shots[n][i].lng], [shots[n][i].lat])
            r1x = []
            r1y = []
            r2x = []
            r2y = []
            r3x = []
            r3y = []
            count = 0
            for leg in shots[n][i].route:
                if leg.pod == 0:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r3x.extend(geo[0])
                        r3y.extend(geo[1])
                    assert len(shots[n][i].route) == 1
                    continue
                count += 1
                if count == 1:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r1x.extend(geo[0])
                        r1y.extend(geo[1])
                else:
                    for step in leg.steps:
                        geo = np.transpose( step.geo )
                        r2x.extend(geo[0])
                        r2y.extend(geo[1])
            routes1[i].set_data( r1x, r1y )
            routes2[i].set_data( r2x, r2y )
            routes3[i].set_data( r3x, r3y )
        return vehs, routes1, routes2, routes3
    
    fig = plt.figure(figsize=(6,6))
    plt.xlim((-2.5,2.5))
    plt.ylim((-2.5,2.5))
    # fig = plt.figure(figsize=(5.52,6.63))
    # plt.xlim((-0.02,0.18))
    # plt.ylim((51.29,51.44))
    # img = mpimg.imread("map.png")
    # plt.imshow(img, extent=[-0.02, 0.18, 51.29, 51.44], aspect=0.2/0.15*6.63/5.52)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    vehs = []
    routes1 = []
    routes2 = []
    routes3 = []
    rejs = []
    for v in reversed(shots[0]):
        color = "0.50"
        if v.id == 0:
            color = "#dc241f"
        elif v.id == 1:
            color = "#9b0058"
        elif v.id == 2:
            color = "#0019a8"
        elif v.id == 3:
            color = "#0098d8"
        elif v.id == 4:
            color = "#b26300"
        vehs.append( plt.plot([], [], color=color, marker='o', markersize=4, alpha=0.7)[0] )
        routes1.append( plt.plot([], [], linestyle='-', color=color, alpha=0.7)[0] )
        routes2.append( plt.plot([], [], linestyle='--', color=color, alpha=0.7)[0] )
        routes3.append( plt.plot([], [], linestyle=':', color=color, alpha=0.4)[0] )
        # rejs.append( plt.arrow(None, None, None, None, color=color, alpha=0.7)[0] )
    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(shots), interval=100)
    return anime

def draw(model):    
    fig = plt.figure(figsize=(6,6))
    plt.xlim((-2.5,2.5))
    plt.ylim((-2.5,2.5))
    # fig = plt.figure(figsize=(5.52,6.63))
    # plt.xlim((-0.02,0.18))
    # plt.ylim((51.29,51.44))
    # img = mpimg.imread("map.png")
    # plt.imshow(img, extent=[-0.02, 0.18, 51.29, 51.44], aspect=0.2/0.15*6.63/5.52)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    for y in range(11):
        plt.plot([-2.5,2.5], [-2.5+y*0.5, -2.5+y*0.5], color="0.3", linestyle=':', linewidth=0.5)
    for x in range(11):
        plt.plot([-2.5+x*0.5, -2.5+x*0.5], [-2.5,2.5], color="0.3", linestyle=':', linewidth=0.5)
    lng = model[-1].lng
    lat = model[-1].lat
    for y in range(6):
        plt.plot([lng-1.25,lng+1.25], [lat-1.25+y*0.5, lat-1.25+y*0.5], color="0.5", linestyle=':', linewidth=0.5)
    for x in range(6):
        plt.plot([lng-1.25+x*0.5, lng-1.25+x*0.5], [lat-1.25,lat+1.25], color="0.5", linestyle=':', linewidth=0.5)
    vehs = []
    routes1 = []
    routes2 = []
    routes3 = []
    rejs = []
    for v in reversed(model):
        color = "0.50"
        if v.id == 0:
            color = "#dc241f"
        # elif v.id == 1:
        #     color = "#9b0058"
        # elif v.id == 2:
        #     color = "#0019a8"
        # elif v.id == 3:
        #     color = "#0098d8"
        # elif v.id == 4:
        #     color = "#b26300"
        vehs.append( plt.plot([], [], color=color, marker='o', markersize=4, alpha=0.7)[0] )
        routes1.append( plt.plot([], [], linestyle='-', color=color, alpha=0.7)[0] )
        routes2.append( plt.plot([], [], linestyle='-', color=color, alpha=0.4)[0] )
        routes3.append( plt.plot([], [], linestyle='--', color=color, alpha=0.4)[0] )
        # rejs.append( plt.arrow(None, None, None, None, color=color, alpha=0.7)[0] )
    for i in range(len(vehs)):
        vehs[i].set_data([model[i].lng], [model[i].lat])
        r1x = []
        r1y = []
        r2x = []
        r2y = []
        r3x = []
        r3y = []
        count = 0
        for leg in model[i].route:
            if leg.pod == 0:
                for step in leg.steps:
                    geo = np.transpose( step.geo )
                    r3x.extend(geo[0])
                    r3y.extend(geo[1])
                # assert len(shots[0][i].route) == 1
                continue
            count += 1
            if count == 1:
                for step in leg.steps:
                    geo = np.transpose( step.geo )
                    r1x.extend(geo[0])
                    r1y.extend(geo[1])
            else:
                for step in leg.steps:
                    geo = np.transpose( step.geo )
                    r2x.extend(geo[0])
                    r2y.extend(geo[1])
        routes1[i].set_data( r1x, r1y )
        routes2[i].set_data( r2x, r2y )
        routes3[i].set_data( r3x, r3y )
    # anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(shots), interval=100)
    # return anime

if __name__ == "__main__":
    exe_loc = './osrm-backend-5.6.0/build/osrm-routed'
    map_loc = './osrm-backend-5.6.0/greater-london-latest.osrm'

    if DIRECT:
        osrm = None
    else:
        osrm = OsrmEngine(exe_loc, map_loc)
        osrm.start_server()
        osrm = OsrmEngine(exe_loc, map_loc)
        osrm.start_server()

    for i in range(1):
        for j in range(1):
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")
            env = RebalancingEnv( Model(DEMAND, TOTAL_DEMAND * DEMAND_SCALER, V=FLEET_SIZE, K=CAPACITY), penalty=-0 )

            nb_actions = env.action_space.n
            input_shape = (1,) + env.state.shape
            input_dim = env.input_dim

            model = Sequential()
            model.add(Flatten(input_shape=input_shape))
            model.add(Dense(256, activation='relu'))
            # model.add(Dense(64, activation='relu'))
            model.add(Dense(nb_actions, activation='linear'))

            memory = SequentialMemory(limit=2000, window_length=1)
            policy = EpsGreedyQPolicy()
            dqn = DQNAgent(model=model, nb_actions=nb_actions, memory=memory, nb_steps_warmup=100,
                           target_model_update=1e-2, policy=policy, gamma=.80)
            dqn.compile(Adam(lr=0.001, epsilon=0.05, decay=0.0), metrics=['mae'])

            # dqn.fit(env, nb_steps=3000, action_repetition=1, visualize=False, verbose=2)
            # dqn.save_weights('dqn_weights_%s.h5f' % (now), overwrite=True)
            dqn.load_weights('dqn_weights_BAL5_150.h5f')

            # anime = anim(env.shots)
            # anime.save('test.mp4', dpi=300, fps=None, extra_args=['-vcodec', 'libx264'])
            # plt.show()

            results = []
            for ii in range(10):
                shots = []
                model = Model(DEMAND, TOTAL_DEMAND * DEMAND_SCALER, dqn=dqn, V=FLEET_SIZE, K=CAPACITY)
                stime = time.time()
                for T in range(0, WARM_UP+SIMULATION+WRAP_UP,ASSIGN_INT):
                    model.dispatch_at_time(osrm, T)
                etime = time.time()
                runtime = etime - stime

                # anime = anim(shots)
                # anime.save('test.mp4', dpi=300, fps=None, extra_args=['-vcodec', 'libx264'])
                # plt.show()

                result = print_results(model, runtime, now)
                results.append(result)
            print("summary: ")
            print(np.average(np.array(results), axis=0))

            # draw(model.vehs)
            # # plt.show()
            # plt.savefig('fig1.eps', format='eps', dpi=1000)


            # if np.average(np.array(results), axis=0)[0] < 160:
            #     dqn.save_weights('dqn_weights_%s.h5f' % (now), overwrite=True)
