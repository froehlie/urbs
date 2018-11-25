import os
import pandas as pd
import pyomo.environ
import shutil
import urbs
from datetime import datetime
from pyomo.opt.base import SolverFactory


if __name__ == '__main__':
    input_file = 'Input'
    result_name = 'Intertemporal'
    # problem without Input folder
    # result_name = os.path.splitext(input_file)[0]  # cut away file extension
    result_dir = urbs.prepare_result_directory(result_name)  # name + time stamp

    # copy input file to result directory
    # shutil.copyfile(input_file, os.path.join(result_dir, input_file))
    # copy runme.py to result directory
    shutil.copy(__file__, result_dir)

    # objective function
    objective = 'cost' # set either 'cost' or 'CO2' as objective

    # Choose Solver (cplex, glpk, gurobi, ...)
    Solver = 'gurobi'

    # simulation timesteps
    (offset, length) = (3000, 168)  # time step selection
    timesteps = range(offset, offset+length+1)
    dt = 1  # length of each time step (unit: hours)

    # plotting commodities/sites
    plot_tuples = [
        (2018, 'North', 'Elec'),
        (2018, 'Mid', 'Elec'),
        (2018, 'South', 'Elec'),
        (2018, ['North', 'Mid', 'South'], 'Elec')]

    # optional: define names for sites in plot_tuples
    
    plot_sites_name = {('North', 'Mid', 'South'): 'All'}
    
    # detailed reporting commodity/sites
    report_tuples = [
        (2018,'North', 'Elec'), (2018,'Mid', 'Elec'), (2018,'South', 'Elec'),
        (2018,'North', 'CO2'), (2018,'Mid', 'CO2'), (2018,'South', 'CO2')]

    # optional: define names for sites in report_tuples
    report_sites_name = {'North': 'Greenland'}

    # # Intertemporal

    # # plotting commodities/sites
    # plot_tuples = [
    #     (2015, 'Campus', 'Elec'),
    #     (2015, 'Campus', 'Heat'),
    #     (2015, 'Campus', 'Cold'),
    #     (2015, 'Campus', 'Heat low'),
    #     (2020, 'Campus', 'Elec'),
    #     (2020, 'Campus', 'Heat'),
    #     (2020, 'Campus', 'Cold'),
    #     (2020, 'Campus', 'Heat low'),
    #     (2025, 'Campus', 'Elec'),
    #     (2025, 'Campus', 'Heat'),
    #     (2025, 'Campus', 'Cold'),
    #     (2025, 'Campus', 'Heat low'),
    #     (2030, 'Campus', 'Elec'),
    #     (2030, 'Campus', 'Heat'),
    #     (2030, 'Campus', 'Cold'),
    #     (2030, 'Campus', 'Heat low'),
    #     (2035, 'Campus', 'Elec'),
    #     (2035, 'Campus', 'Heat'),
    #     (2035, 'Campus', 'Cold'),
    #     (2035, 'Campus', 'Heat low'),
    #     (2040, 'Campus', 'Elec'),
    #     (2040, 'Campus', 'Heat'),
    #     (2040, 'Campus', 'Cold'),
    #     (2040, 'Campus', 'Heat low')
    #     ]

    # # optional: define names for sites in plot_tuples
    # plot_sites_name = {}

    # # detailed reporting commodity/sites
    # report_tuples = [
    #     (2015, 'Campus', 'Elec'),
    #     (2015, 'Campus', 'Heat'),
    #     (2015, 'Campus', 'Cold'),
    #     (2015, 'Campus', 'Heat low'),
    #     (2015, 'Campus', 'CO2'),
    #     (2020, 'Campus', 'Elec'),
    #     (2020, 'Campus', 'Heat'),
    #     (2020, 'Campus', 'Cold'),
    #     (2020, 'Campus', 'CO2'),
    #     (2020, 'Campus', 'Heat low'),
    #     (2025, 'Campus', 'Elec'),
    #     (2025, 'Campus', 'Heat'),
    #     (2025, 'Campus', 'Cold'),
    #     (2025, 'Campus', 'Heat low'),
    #     (2025, 'Campus', 'CO2'),
    #     (2030, 'Campus', 'Elec'),
    #     (2030, 'Campus', 'Heat'),
    #     (2030, 'Campus', 'Cold'),
    #     (2030, 'Campus', 'Heat low'),
    #     (2030, 'Campus', 'CO2'),
    #     (2035, 'Campus', 'Elec'),
    #     (2035, 'Campus', 'Heat'),
    #     (2035, 'Campus', 'Cold'),
    #     (2035, 'Campus', 'Heat low'),
    #     (2035, 'Campus', 'CO2'),
    #     (2040, 'Campus', 'Elec'),
    #     (2040, 'Campus', 'Heat'),
    #     (2040, 'Campus', 'Cold'),
    #     (2040, 'Campus', 'Heat low'),
    #     (2040, 'Campus', 'CO2'),
    #     ]

    # # optional: define names for sites in report_tuples
    # report_sites_name = {}

    # plotting timesteps
    plot_periods = {
        'all': timesteps[1:]
    }

    # add or change plot colors
    my_colors = {
        'South': (230, 200, 200),
        'Mid': (200, 230, 200),
        'North': (200, 200, 230)}
    for country, color in my_colors.items():
        urbs.COLORS[country] = color

    # select scenarios to be run
    scenarios = [
        urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_base,
        # urbs.scenario_stock_prices,
        # urbs.scenario_co2_limit
        # urbs.scenario_co2_tax_mid,
        # urbs.scenario_no_dsm,
        # urbs.scenario_north_process_caps,
        # urbs.scenario_all_together
        ]

    # create timelog
    timelog = open(os.path.join(result_dir, "timelog.txt"), "a")
    timelog.write("Total\tread\tmodel\tsolve\tplot\r\n")
    timelog.close()

    for scenario in scenarios:
        prob = urbs.run_scenario(input_file, Solver, timesteps, scenario, 
                            result_dir, dt, objective, 
                            plot_tuples=plot_tuples,
                            plot_sites_name=plot_sites_name,
                            plot_periods=plot_periods,
                            report_tuples=report_tuples,
                            report_sites_name=report_sites_name)

    # open timelog file
    os.startfile(os.path.join(result_dir, "timelog.txt"))
