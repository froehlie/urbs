import os
import pyomo.environ
import time
from pyomo.opt.base import SolverFactory
from datetime import datetime
from .model import create_model
from .report import *
from .plot import *
from .input import *
from .validation import *
from .saveload import save


def prepare_result_directory(result_name):
    """ create a time stamped directory within the result folder """
    # timestamp for result directory
    now = datetime.now().strftime('%Y%m%dT%H%M')

    # create result directory if not existent
    result_dir = os.path.join('result', '{}-{}'.format(result_name, now))
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    return result_dir


def setup_solver(optim, logfile='solver.log'):
    """ """
    if optim.name == 'gurobi':
        # reference with list of option names
        # http://www.gurobi.com/documentation/5.6/reference-manual/parameters
        optim.set_options("logfile={}".format(logfile))
        # optim.set_options("timelimit=7200")  # seconds
        # optim.set_options("mipgap=5e-4")  # default = 1e-4
    elif optim.name == 'glpk':
        # reference with list of options
        # execute 'glpsol --help'
        optim.set_options("log={}".format(logfile))
        # optim.set_options("tmlim=7200")  # seconds
        # optim.set_options("mipgap=.0005")
    else:
        print("Warning from setup_solver: no options set for solver "
              "'{}'!".format(optim.name))
    return optim


def run_scenario(input, Solver, timesteps, scenario, result_dir, dt, objective, 
                 plot_tuples=None,  plot_sites_name=None, plot_periods=None,
                 report_tuples=None, report_sites_name=None):
    """ run an urbs model for given input, time steps and scenario

    Args:
        input_file: filename to an Excel spreadsheet for urbs.read_excel
        timesteps: a list of timesteps, e.g. range(0,8761)
        scenario: a scenario function that modifies the input data dict
        result_dir: directory name for result spreadsheet and plots
        dt: length of each time step (unit: hours)
        plot_tuples: (optional) list of plot tuples (c.f. urbs.result_figures)
        plot_sites_name: (optional) dict of names for sites in plot_tuples
        plot_periods: (optional) dict of plot periods(c.f. urbs.result_figures)
        report_tuples: (optional) list of (sit, com) tuples (c.f. urbs.report)
        report_sites_name: (optional) dict of names for sites in report_tuples

    Returns:
        the urbs model instance
    """

    # start time measurement
    start_time = time.process_time()

    # scenario name, read and modify data for scenario
    sce = scenario.__name__
    data, mode = read_input(input)
    data = scenario(data)
    validate_input(data)

    # measure time to read file
    read_time = time.process_time()
    print("Time to read file: %.2f sec" % (read_time - start_time))

    # create model
    prob = create_model(data, mode, dt, timesteps, objective)
    # prob.write('model.lp', io_options={'symbolic_solver_labels':True})

    # measure time to create model
    model_time = time.process_time()
    print("Time to create model: %.2f sec" % (model_time - read_time))

    # refresh time stamp string and create filename for logfile
    now = prob.created
    log_filename = os.path.join(result_dir, '{}.log').format(sce)

    # solve model and read results
    optim = SolverFactory(Solver)  # cplex, glpk, gurobi, ...
    optim = setup_solver(optim, logfile=log_filename)
    result = optim.solve(prob, tee=True)

    # save problem solution (and input data) to HDF5 file
    save(prob, os.path.join(result_dir, '{}.h5'.format(sce)))

    # write report to spreadsheet
    report(
        prob,
        os.path.join(result_dir, '{}.xlsx').format(sce),
        report_tuples=report_tuples,
        report_sites_name=report_sites_name)

    # result plots
    result_figures(
        prob,
        os.path.join(result_dir, '{}'.format(sce)),
        timesteps,
        plot_title_prefix=sce.replace('_', ' '),
        plot_tuples=plot_tuples,
        plot_sites_name=plot_sites_name,
        periods=plot_periods,
        figure_size=(24, 9))

    # measure time to run scenario
    sce_time = time.process_time()
    print("Time to run scenario: %.2f sec" % (sce_time - start_time))

    # write time measurements into file "timelog.txt" in result directory
    timelog = open(os.path.join(result_dir, "timelog.txt"), "a")
    timelog.write("Scenario: %s \r\n" % sce)
    timelog.write("Time to run scenario: %.2f sec \r\n"
                  % (sce_time - start_time))
    timelog.write("Time to read file: %.2f sec \r\n"
                  % (read_time - start_time))
    timelog.write("Time to create model: %.2f sec \r\n\r\n"
                  % (model_time - read_time))

    return prob