import pandas as pd
from .input import get_input
from .output import get_constants, get_timeseries
from .util import is_string


def report(instance, filename, report_tuples=None, report_sites_name={}):
    """Write result summary to a spreadsheet file

    Args:
        instance: a urbs model instance
        filename: Excel spreadsheet filename, will be overwritten if exists
        report_tuples: (optional) list of (sit, com) tuples for which to
                       create detailed timeseries sheets
        report_sites_name: (optional) dict of names for created timeseries
                       sheets
    Returns:
        Nothing
    """
    # default to all demand (sit, com) tuples if none are specified
    if report_tuples is None:
        report_tuples = get_input(instance, 'demand').columns

    costs, cpro, csto = get_constants(instance)

    # create spreadsheet writer object
    with pd.ExcelWriter(filename) as writer:

        # write constants to spreadsheet
        costs.to_frame().to_excel(writer, 'Costs')
        cpro.to_excel(writer, 'Process caps')
        csto.to_excel(writer, 'Storage caps')

        # initialize timeseries tableaus
        energies = []
        timeseries = {}
        help_ts = {}

        # collect timeseries data
        for sit, com in report_tuples:

            # wrap single site name in 1-element list for consistent behavior
            if is_string(sit):
                help_sit = [sit]
            else:
                help_sit = sit
                sit = tuple(sit)

            # check existence of predefined names, else define them
            try:
                report_sites_name[sit]
            except:
                report_sites_name[sit] = str(sit)

            for lv in help_sit:
                (created, consumed, stored, 
                 dsm) = get_timeseries(instance, com, lv)

                overprod = pd.DataFrame(
                    columns=['Overproduction'],
                    data=created.sum(axis=1) - consumed.sum(axis=1) +
                    stored['Retrieved'] - stored['Stored'])

                tableau = pd.concat(
                    [created, consumed, stored, overprod,
                     dsm],
                    axis=1,
                    keys=['Created', 'Consumed', 'Storage', 'Import from',
                          'Export to', 'Balance', 'DSM'])
                help_ts[(lv, com)] = tableau.copy()

                # timeseries sums
                help_sums = pd.concat([created.sum(), consumed.sum(),
                                       stored.sum().drop('Level'),
                                       overprod.sum(), dsm.sum()],
                                      axis=0,
                                      keys=['Created', 'Consumed', 'Storage',
                                            'Import', 'Export', 'Balance',
                                            'DSM'])
                try:
                    timeseries[(report_sites_name[sit], com)] = timeseries[
                        (report_sites_name[sit], com)].add(
                            help_ts[(lv, com)], axis=1, fill_value=0)
                    sums = sums.add(help_sums, fill_value=0)
                except:
                    timeseries[(report_sites_name[sit], com)] = help_ts[
                        (lv, com)]
                    sums = help_sums

            energies.append(sums.to_frame("{}.{}".format(
                report_sites_name[sit], com)))

        # write timeseries data (if any)
        if timeseries:
            # concatenate Commodity sums
            energy = pd.concat(energies, axis=1).fillna(0)
            energy.to_excel(writer, 'Commodity sums')

            # write timeseries to individual sheets
            for sit, com in report_tuples:
                if isinstance(sit, list):
                    sit = tuple(sit)
                # sheet names cannot be longer than 31 characters...
                sheet_name = "{}.{} timeseries".format(
                    report_sites_name[sit], com)[:31]
                timeseries[(report_sites_name[sit], com)].to_excel(
                    writer, sheet_name)
