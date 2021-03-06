import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .helpers import determine_tag_value, figs_assert, initiate_figs, plot_helper_settings
from ..xml_utils import parse


def get_tdos(filepath='DOSCAR', ISPIN=None, Ef=None, plot=False, xlim=None, ylim_upper=None, on_figs=None):
    """
    Get the total density of states, with consideration of spin-polarization.
    Accepts file type 'DOSCAR', or 'vasprun.xml'.

    Parameters
    ----------
    filepath: string
        filepath, default to 'DOSCAR'
        For DOSCAR-type file, can be any string containing 'DOSCAR'.
        For vasprun.xml-type file, can be any string ending with '.xml'.
    ISPIN: int
        user specified ISPIN
        If not given, for DOSCAR-type file, infer from 'OUTCAR'/'INCAR'.
    Ef: float
        user specified Ef
    plot: bool
        whether to plot the data, default to False
    xlim: list
        the range of x-axis, 2 values in a list
    ylim_upper: int/float
        the upper limit of y-axis(, of the spin-combined plot if ISPIN == 2)
    on_figs: list/int
        the current figure numbers to plot to, default to new figures

    Returns
    -------
    a dict, containing
        'data': a pandas dataframe
        'ax': the axes reference
    """
    # get data
    if re.match(r".*\.xml", filepath):
        root = parse(filepath)

        NEDOS = int(root.find("./parameters/separator[@name='dos']/i[@name='NEDOS']").text)
        Ef = float(root.find("./calculation/dos/i[@name='efermi']").text)
        if ISPIN:
            print("Using user specified ISPIN.")
        else:
            ISPIN = int(root.find(
                "./parameters/separator[@name='electronic']/separator[@name='electronic spin']/i[@name='ISPIN']").text)

        if ISPIN == 1:
            data = np.zeros((NEDOS, 3))
            for n_step, elem in enumerate(root.findall(
                    "./calculation/dos/total/array/set/set[@comment='spin 1']/r")):
                data[n_step] = elem.text.split()

        elif ISPIN == 2:
            data1 = np.zeros((NEDOS, 3))
            for n_step, elem in enumerate(root.findall(
                    "./calculation/dos/total/array/set/set[@comment='spin 1']/r")):
                data1[n_step] = elem.text.split()
            data2 = np.zeros((NEDOS, 3))
            for n_step, elem in enumerate(root.findall(
                    "./calculation/dos/total/array/set/set[@comment='spin 2']/r")):
                data2[n_step] = elem.text.split()

    elif re.match(r".*DOSCAR.*", filepath):
        with open(filepath, 'r') as f:
            DOSCAR = f.readlines()
        for i in range(len(DOSCAR)):
            DOSCAR[i] = DOSCAR[i].split()

        NEDOS = int(DOSCAR[5][2])
        Ef = float(DOSCAR[5][3])
        if ISPIN:
            print("Using user specified ISPIN.")
        else:
            ISPIN = determine_tag_value('ISPIN', filepath)

        data = np.array(DOSCAR[6:6 + NEDOS], dtype=float)
        if ISPIN == 2:
            data1 = data[:, [0, 1, 3]]
            data2 = data[:, [0, 2, 4]]

    # confluence and data organizing
    if ISPIN == 1:
        col_names = ['E', 'tot', 'tot_integrated']
        data[:, 0] -= Ef
        return_dict = {'data': pd.DataFrame(**{'columns': col_names, 'data': data})}
    elif ISPIN == 2:
        col_names1 = ['E', 'tot_up', 'tot_integrated_up']
        col_names2 = ['E', 'tot_down', 'tot_integrated_down']
        data1[:, 0] -= Ef
        data2[:, 0] -= Ef
        return_dict = {'data_spin_up': pd.DataFrame(**{'columns': col_names1, 'data': data1}),
                       'data_spin_down': pd.DataFrame(**{'columns': col_names2, 'data': data2}),
                       }

    if plot:
        # start plotting
        figs_assert(on_figs, ISPIN, 'tdos')

        if ISPIN == 1:
            initiate_figs(on_figs)
            plt.plot(data[:, 0], data[:, 1])
            ax = plt.gca()
            plot_helper_settings((xlim, [0, ylim_upper]), 'tdos')
            return_dict.update({'ax': ax})

        elif ISPIN == 2:
            # Plot the combined TDOS
            initiate_figs(on_figs)
            plt.plot(data1[:, 0], data1[:, 1] + data2[:, 1], label='spin up + down')
            ax1 = plt.gca()
            plot_helper_settings((xlim, [0, ylim_upper]), 'tdos')
            # Plot the separated TDOS
            initiate_figs(on_figs)
            plt.plot(data1[:, 0], data1[:, 1], label='spin up')
            plt.plot(data2[:, 0], -data2[:, 1], label='spin down')
            ax2 = plt.gca()
            ylim_upper_sp = None
            ylim_lower_sp = None
            if ylim_upper:
                ylim_upper_sp = ylim_upper/2.
                ylim_lower_sp = -ylim_upper_sp
            plot_helper_settings((xlim, [ylim_lower_sp, ylim_upper_sp]), 'tdos')
            return_dict.update({'ax_spin_combined': ax1, 'ax_spin_separated': ax2})

    return return_dict


def get_ldos(atom, filepath='DOSCAR', ISPIN=None, LORBIT=None, Ef=None, plot=False, xlim=None, ylim_upper=None,
             on_figs=None):
    """
    Get the local projected density of states, with consideration of spin-polarization.
    Accepts file type 'DOSCAR', or 'vasprun.xml'.

    Parameters
    ----------
    atom: int
        the atom number in DOSCAR/POSCAR interested, counting from 1
    filepath: string
        filepath, default to 'DOSCAR'
        For DOSCAR-type file, can be any string containing 'DOSCAR'.
        For vasprun.xml-type file, can be any string ending with '.xml'.
    ISPIN: int
        user specified ISPIN
        If not given, for DOSCAR-type file, infer from 'OUTCAR'/'INCAR'.
    LORBIT: int
        user specified LORBIT
        If not given, for both DOSCAR- and vasprun.xml-types of file, infer from 'OUTCAR'/'INCAR'. Because there is an
        error in vasprun.xml.
    Ef: float
        user specified Ef
    plot: bool
        whether to plot the data, default to False
    xlim: list
        the range of x-axis, 2 values in a list
    ylim_upper: int/float
        the upper limit of y-axis(, of the spin-combined plot if ISPIN == 2)
    on_figs: list/int
        the current figure numbers to plot to, default to new figures

    Returns
    -------
    a dict, containing
        'data': a dataframe
        'ax': the axes reference
    """
    # get data
    if re.match(r".*\.xml", filepath):
        root = parse(filepath)

        NEDOS = int(root.find("./parameters/separator[@name='dos']/i[@name='NEDOS']").text)
        Ef = float(root.find("./calculation/dos/i[@name='efermi']").text)
        if ISPIN:
            print("Using user specified ISPIN.")
        else:
            ISPIN = int(root.find(
                "./parameters/separator[@name='electronic']/separator[@name='electronic spin']/i[@name='ISPIN']").text)
        # vasprun.xml's LORBIT is not correct
        if LORBIT:
            print("Using user specified LORBIT.")
        else:
            LORBIT = determine_tag_value('LORBIT', filepath)

        if ISPIN == 1:
            if LORBIT == 10 or LORBIT == 0:
                data = np.zeros((NEDOS, 4))
            elif LORBIT == 11 or LORBIT == 1:
                data = np.zeros((NEDOS, 10))
            for n_step, elem in enumerate(root.findall(
                                    "./calculation/dos/partial/array/set/set[@comment='ion " + str(
                                    atom) + "']/set[@comment='spin 1']/r")):
                data[n_step] = elem.text.split()

        elif ISPIN == 2:
            if LORBIT == 10 or LORBIT == 0:
                data1 = np.zeros((NEDOS, 4))
                data2 = np.zeros((NEDOS, 4))
            elif LORBIT == 11 or LORBIT == 1:
                data1 = np.zeros((NEDOS, 10))
                data2 = np.zeros((NEDOS, 10))

            for n_step, elem in enumerate(root.findall(
                                    "./calculation/dos/partial/array/set/set[@comment='ion " + str(
                                    atom) + "']/set[@comment='spin 1']/r")):
                data1[n_step] = elem.text.split()
            for n_step, elem in enumerate(root.findall(
                                    "./calculation/dos/partial/array/set/set[@comment='ion " + str(
                                    atom) + "']/set[@comment='spin 2']/r")):
                data2[n_step] = elem.text.split()

    elif re.match(r".*DOSCAR.*", filepath):
        with open(filepath, 'r') as f:
            DOSCAR = f.readlines()
        for i in range(len(DOSCAR)):
            DOSCAR[i] = DOSCAR[i].split()

        NEDOS = int(DOSCAR[5][2])
        Ef = float(DOSCAR[5][3])
        if ISPIN:
            print("Using user specified ISPIN.")
        else:
            ISPIN = determine_tag_value('ISPIN', filepath)
        if LORBIT:
            print("Using user specified LORBIT.")
        else:
            LORBIT = determine_tag_value('LORBIT', filepath)

        data = np.array(DOSCAR[(6 + (NEDOS + 1) * atom):(6 + (NEDOS + 1) * atom + NEDOS)], dtype=float)
        if ISPIN == 2:
            if LORBIT == 10 or LORBIT == 0:
                data1 = data[:, [0, 1, 3, 5]]
                data2 = data[:, [0, 2, 4, 6]]
            elif LORBIT == 11 or LORBIT == 1:
                data1 = data[:, [0, 1, 3, 5, 7, 9, 11, 13, 15, 17]]
                data2 = data[:, [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]]

    # confluence and data organizing
    if ISPIN == 1:
        if LORBIT == 10 or LORBIT == 0:
            col_names = ['E', 's', 'p', 'd']
        elif LORBIT == 11 or LORBIT == 1:
            col_names = ['E', 's', 'p_y', 'p_z', 'p_x', 'd_xy', 'd_yz', 'd_z2', 'd_xz', 'd_x2y2']
        data[:, 0] -= Ef
        return_dict = {'data': pd.DataFrame(**{'columns': col_names, 'data': data})}
    elif ISPIN == 2:
        if LORBIT == 10 or LORBIT == 0:
            col_names1 = ['E', 's_up', 'p_up', 'd_up']
            col_names2 = ['E', 's_down', 'p_down', 'd_down']
        elif LORBIT == 11 or LORBIT == 1:
            col_names1 = ['E', 's_up', 'p_y_up', 'p_z_up', 'p_x_up', 'd_xy_up', 'd_yz_up', 'd_z2_up', 'd_xz_up',
                          'd_x2y2_up']
            col_names2 = ['E', 's_down', 'p_y_down', 'p_z_down', 'p_x_down', 'd_xy_down', 'd_yz_down', 'd_z2_down',
                          'd_xz_down', 'd_x2y2_down']
        data1[:, 0] -= Ef
        data2[:, 0] -= Ef
        return_dict = {'data_spin_up': pd.DataFrame(**{'columns': col_names1, 'data': data1}),
                       'data_spin_down': pd.DataFrame(**{'columns': col_names2, 'data': data2}),
                       }

    if plot:
        # start plotting
        figs_assert(on_figs, ISPIN, 'ldos')

        if ISPIN == 1:
            initiate_figs(on_figs)
            if LORBIT == 10 or LORBIT == 0:
                for i in range(1, 4):
                    plt.plot(data[:, 0], data[:, i], label=col_names[i])
            elif LORBIT == 11 or LORBIT == 1:
                for i in range(1, 10):
                    plt.plot(data[:, 0], data[:, i], label=col_names[i])
            ax = plt.gca()
            plot_helper_settings((xlim, [0, ylim_upper]), 'ldos')
            return_dict.update({'ax': ax})

        elif ISPIN == 2:
            # plot spin combined
            initiate_figs(on_figs)
            if LORBIT == 10 or LORBIT == 0:
                for i in range(1, 4):
                    plt.plot(data1[:, 0], data1[:, i] + data2[:, i], label=col_names1[i] + ' + ' + col_names2[i])
            elif LORBIT == 11 or LORBIT == 1:
                for i in range(1, 10):
                    plt.plot(data1[:, 0], data1[:, i] + data2[:, i], label=col_names1[i] + ' + ' + col_names2[i])
            ax1 = plt.gca()
            plot_helper_settings((xlim, [0, ylim_upper]), 'ldos')
            # plot spin separated
            initiate_figs(on_figs)
            if LORBIT == 10 or LORBIT == 0:
                for i in range(1, 4):
                    plt.plot(data1[:, 0], data1[:, i], label=col_names1[i])
                    plt.plot(data2[:, 0], -data2[:, i], label=col_names2[i])
            elif LORBIT == 11 or LORBIT == 1:
                for i in range(1, 10):
                    plt.plot(data1[:, 0], data1[:, i], label=col_names1[i])
                    plt.plot(data2[:, 0], -data2[:, i], label=col_names2[i])
            ax2 = plt.gca()
            ylim_upper_sp = None
            ylim_lower_sp = None
            if ylim_upper:
                ylim_upper_sp = ylim_upper/2.
                ylim_lower_sp = -ylim_upper_sp
            plot_helper_settings((xlim, [ylim_lower_sp, ylim_upper_sp]), 'ldos')
            return_dict.update({'ax_spin_combined': ax1, 'ax_spin_separated': ax2})

    return return_dict

