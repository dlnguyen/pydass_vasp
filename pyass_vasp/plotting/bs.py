import re
import warnings
import numpy as np
import matplotlib.pyplot as plt
from helpers import determine_tag_value, plot_helper_figs_assert, plot_helper_figs
from ..xml_utils import parse


# Effective mass calculation funcitons.
def find_band_edges(kp_edge, prec_range, E):
    """
    Given the k-point index number on the x-axis, search for the indices of bands
    right below or above Ef.

    Parameters
    ----------
    kp_edge : int
        The k-point index number that corresponds to the band edges (VBM and CBM).
    prec_range : float
        The searching range in eV.
    E : 2D numpy array
        The 2D array that contains eigenvalues. Each row denotes a k-point, and each column a band.
    """
    # Examine valence band edge.
    print 'The possible valence bands are', \
        np.where(np.logical_and(E[kp_edge] > -prec_range, E[kp_edge] < 0))[1]
    # Examine conduction band edge.
    print 'The possible conduction bands are', \
        np.where(np.logical_and(E[kp_edge] < prec_range, E[kp_edge] > 0))[1]


def get_reduced_effective_mass(band, kp_start, kp_end, kps_linearized, E):
    """
    Given the band index number, k-point start and end indices, fit the included curve
    to a 2nd-order polynomial, and obtain the effective mass of the carrier electron or hole.

    Parameters
    ----------
    band : int
        The band index number of interest.
    kp_start : int
        The index number of the starting k-point.
    kp_end : int
        The index number of the ending k-point.
    kps_linearized : 1D numpy array
        The full x-axis of k-points.
    E : 2D numpy array
        The 2D array that contains eigenvalues. Each row denotes a k-point, and each column a band.

    Returns
    -------
    the reduced effective mass
    """
    h_bar = 1.054571726e-34
    e = 1.6021176462e-19
    m_e = 9.10938291e-31
    scaling_const = 6.3743775177e-10

    # Decide on the fitting range, characterized by indices.
    selected_kp_array = kps_linearized[kp_start:kp_end + 1]
    selected_energy_array = E[kp_start:kp_end + 1, band]
    p = np.poly1d(np.polyfit(selected_kp_array, selected_energy_array, 2))
    axis_fitted = -p[1]/2/p[2]
    axis_actual = selected_kp_array[selected_energy_array.argmin() if p[2] > 0 else selected_energy_array.argmax()]
    print "The fitted x coord at energy extrema is {0}, and the actual is {1}.".format(axis_fitted, axis_actual)
    k_fit = np.linspace(kps_linearized[kp_start], kps_linearized[kp_end], 200)
    plt.plot(k_fit, p(k_fit), lw=2)

    d2E_dk2 = e * p[2] / (2 * np.pi / scaling_const) ** 2
    effective_mass_reduced = h_bar ** 2 / d2E_dk2 / m_e
    return effective_mass_reduced


# internal
def plot_helper_settings(ax, axis_range, reciprocal_point_locations, reciprocal_points, save_figs, output):
    plt.xlim(reciprocal_point_locations[0], reciprocal_point_locations[-1])
    ax.xaxis.set_ticks(reciprocal_point_locations)
    ax.xaxis.set_ticklabels(reciprocal_points)
    plt.axhline(0, ls='--', c='k', alpha=0.5)
    if axis_range:
        plt.ylim(axis_range[0], axis_range[1])
    for kp_end_point in range(len(reciprocal_point_locations)):
        plt.axvline(reciprocal_point_locations[kp_end_point], ls='--', c='k', alpha=0.5)
    plt.ylabel('Energy (eV)')
    # with warnings.catch_warnings():
    #     plt.legend(loc=0, fontsize='small')
    plt.legend(fontsize='small')
    try:
        plt.tight_layout()
    except RuntimeError:
        print "Tight layout failed... Not a big deal though."
    if save_figs:
        plt.savefig(output)


def plot_bs(axis_range=None, ISPIN=None, N_kps_per_section=None, reciprocal_points=None, Ef=None, input_file='EIGENVAL', display=True,
    on_figs=None, close_figs=False, save_figs=False, save_data=False, output_prefix='BS'):
    """
    Plot the band structure, with consideration of spin-polarization.
    Accepts input file 'EIGENVAL', or 'vasprun.xml'.

    Parameters
    ----------
    axis_range: list
        the range of axes x and y, 4 values in a list
    ISPIN: int
        user specified ISPIN. If not given, for 'EIGENVAL' input, infer from 'OUTCAR'/'INCAR'
        for 'vasprun.xml' input, infer from 'vasprun.xml'
    N_kps_per_section: int
        ser specified number of k-points per line section
    reciprocal_points: list
        list of reciprocal point string symbols, like ['G','X','A']
    Ef: float
        user specified Ef. If not given, for 'EIGENVAL' input, infer from 'OUTCAR'/'DOSCAR'
        for 'vasprun.xml' input, infer from 'vasprun.xml'
    input_file: string
        input file name, default to 'EIGENVAL'. Can also be 'vasprun.xml'
    display: bool
        display figures or not
    on_figs: list
        the current figure numbers to plot to, default to new figures
    close_figs: bool
        close figs after drawing. Figures leave axes handlers in memory when the function is called.
        If you care about memory usage, this might be useful.
    save_figs: bool
        save figures or not
    save_data: bool
        save data or not
    output_prefix: string
        prefix string before the output files, default to 'BS'

    Returns
    -------
    a dict, containing
        'reciprocal_points', the symbols of those points
        'reciprocal_point_locations', their locations on the x-axis
        'data', a dict that has 2D array of data,
            easily to Pandas DataFrame by pd.DataFrame(**returned_dict['data'])
        'axes': a dict that contains axes handlers of current figures
    """
    if re.match(r".*\.xml", input_file):
        root = parse(input_file)

        if ISPIN:
            print "Using user specified ISPIN."
        else:
            ISPIN = int(root.find(
            "./parameters/separator[@name='electronic']/separator[@name='electronic spin']/i[@name='ISPIN']").text)
        if Ef:
            print "Using user specified Ef."
        else:
            Ef = float(root.find("./calculation/dos/i[@name='efermi']").text)

        N_bands = int(root.find("./parameters/separator[@name='electronic']/i[@name='NBANDS']").text)
        N_kps_per_section = int(root.find("./kpoints/generation[@param='listgenerated']/i[@name='divisions']").text)
        N_kp_sections = len(root.findall("./kpoints/generation[@param='listgenerated']/v")) - 1
        N_kps = len(root.findall("./kpoints/varray[@name='kpointlist']/v"))
        assert N_kps_per_section * N_kp_sections == N_kps, \
            "The product of N of kpoints per section and N of sections does not match N of total kpoints. Strange."

        # get reciprocal point symbols
        if reciprocal_points:
            print "Using user specified reciprocal point symbols."
        else:
            try:
                with open('OUTCAR', 'r') as f:
                    for line in f:
                        if re.match(r".*k-points in units of 2pi/SCALE and weight:.*", line):
                            reciprocal_points = line.replace(
                                'k-points in units of 2pi/SCALE and weight:', '').strip().split('-')
                            break
            except IOError:
                try:
                    with open('KPOINTS', 'r') as f:
                        KPOINTS = f.readlines()
                    reciprocal_points = KPOINTS[0].strip().split('-')
                except IOError:
                    print ("Can't determine reciprocal point symbols! Either manually specify it, or provide OUTCAR/KPOINTS.")

        kps = np.zeros((N_kps, 3))
        for n_kp, elem in enumerate(root.findall("./kpoints/varray[@name='kpointlist']/v")):
                kps[n_kp] = elem.text.split()[0]

    elif re.match(r".*EIGENVAL.*", input_file):
        # get ISPIN
        if ISPIN:
            print "Using user specified ISPIN."
        else:
            ISPIN = determine_tag_value('ISPIN')
        # get Ef
        if Ef:
            print "Using user specified Ef."
        else:
            try:
                with open('OUTCAR') as f:
                    for line in f:
                        if re.match(r"\s*E-fermi :.*", line):
                            Ef = float(line.split()[2])
            except IOError:
                try:
                    with open('DOSCAR', 'r') as f:
                        for i in range(6):
                            line = f.readline()
                    # Fermi energy. Found in DOSCAR, 6th line, 4th number.
                    Ef = float(line.split()[3])
                except IOError:
                    raise IOError("Can't determine Ef! Either manually specify it, or provide OUTCAR/DOSCAR.")

        # read the main file
        with open(input_file, 'r') as f:
            EIGENVAL = f.readlines()
        for i in range(len(EIGENVAL)):
            EIGENVAL[i] = EIGENVAL[i].split()
        # How many bands are to be drawn? 6th line, 3rd number.
        N_bands = int(EIGENVAL[5][2])
        # How many KPs in total? Can be found in EIGENVAL, 6th line, 2nd number.
        N_kps = int(EIGENVAL[5][1])

        # get nkp per sections
        if N_kps_per_section:
            print "Using user specified number of k-points per line section."
        else:
            try:
                with open('KPOINTS', 'r') as f:
                    KPOINTS = f.readlines()
                N_kps_per_section = int(KPOINTS[1])
            except IOError:
                raise IOError(
                    "Can't determine number of k-points per line section! Either manually specify it, or provide KPOINTS.")

        N_kp_sections = N_kps / N_kps_per_section

        # get the start and end point coordinate of each section. From OUTCAR.
        kps = np.zeros((N_kps, 3))
        with open('OUTCAR', 'r') as f:
            for line in f:
                if re.match(r".*k-points in units of 2pi/SCALE and weight:.*", line):
                    if reciprocal_points:
                        print "Using user specified reciprocal point symbols."
                    else:
                        reciprocal_points = line.replace(
                            'k-points in units of 2pi/SCALE and weight:', '').strip().split('-')
                    break
            for kp in range(N_kps):
                kps[kp] = f.next().split()[:3]

    # confluence of two processing approaches
    # generate the section pairs
    kp_section_pairs = np.zeros((N_kp_sections, 2, 3))
    for section in range(N_kp_sections):
        kp_section_pairs[section] = [kps[N_kps_per_section * section],
                                                    kps[N_kps_per_section * (section + 1) - 1]]

    # Gerenate the linearized kps_linearized as x-axis.
    reciprocal_point_locations = np.zeros(N_kp_sections + 1)
    kps_linearized_sectioned = np.zeros((N_kp_sections, N_kps_per_section))
    for section, section_pair in enumerate(kp_section_pairs):
        reciprocal_point_locations[section + 1] = reciprocal_point_locations[section] + np.linalg.norm(
            section_pair[1] - section_pair[0])
        kps_linearized_sectioned[section] = np.linspace(reciprocal_point_locations[section],
                                                           reciprocal_point_locations[section + 1], N_kps_per_section)
    kps_linearized = kps_linearized_sectioned.flatten()

    if ISPIN == 1:
        col_names = [str(i) for i in range(N_bands + 1)]
        col_names[0] = 'k_points'
    elif ISPIN == 2:
        col_names1 = [str(i) + '_up' for i in range(N_bands + 1)]
        col_names1[0] = 'k_points'
        col_names2 = [str(i) + '_down' for i in range(N_bands + 1)]
        col_names2[0] = 'k_points'

    return_dict = {
        'reciprocal_points': reciprocal_points,
        'reciprocal_point_locations': reciprocal_point_locations
    }

    # diverging again
    if re.match(r".*\.xml", input_file):
        if ISPIN == 1:
            E = np.zeros((N_kps, N_bands))
            for n_kp in range(N_kps):
                for n_band, elem in enumerate(root.findall(
                    "./calculation/eigenvalues/array/set/set[@comment='spin 1']/set[@comment='kpoint "
                    + str(n_kp) + "']/r")):
                    E[n_kp, n_band] = elem.text.split()[0]

        if ISPIN == 2:
            E_spin1 = np.zeros((N_kps, N_bands))
            for n_kp in range(N_kps):
                for n_band, elem in enumerate(root.findall(
                    "./calculation/eigenvalues/array/set/set[@comment='spin 1']/set[@comment='kpoint "
                    + str(n_kp) + "']/r")):
                    E_spin1[n_kp, n_band] = elem.text.split()[0]
            E_spin2 = np.zeros((N_kps, N_bands))
            for n_kp in range(N_kps):
                for n_band, elem in enumerate(root.findall(
                    "./calculation/eigenvalues/array/set/set[@comment='spin 2']/set[@comment='kpoint "
                    + str(n_kp) + "']/r")):
                    E_spin2[n_kp, n_band] = elem.text.split()[0]

    elif re.match(r".*EIGENVAL.*", input_file):
        if ISPIN == 1:
            E = np.zeros((N_kps, N_bands))
            for kp in range(0, N_kps):
                for band in range(0, N_bands):
                    E[kp, band] = float(EIGENVAL[8 + band + (N_bands + 2) * kp][1])

        if ISPIN == 2:
            E_spin1 = np.zeros((N_kps, N_bands))
            E_spin2 = np.zeros((N_kps, N_bands))
            for kp in range(0, N_kps):
                for band in range(0, N_bands):
                    E_spin1[kp, band] = float(EIGENVAL[8 + band + (N_bands + 2) * kp][1])
                    E_spin2[kp, band] = float(EIGENVAL[8 + band + (N_bands + 2) * kp][2])

    # partial confluence
    if ISPIN == 1:
        E -= Ef
        # Plot the bands.
        plot_helper_figs(on_figs)
        ax = plt.subplot(111)
        for band in range(N_bands):
            plt.plot(kps_linearized, E[:, band])
        plot_helper_settings(ax, axis_range, reciprocal_point_locations, reciprocal_points,
                             save_figs, output_prefix+'.pdf')
        axes = {'ax': ax}
        return_dict['data'] = {
                'columns': col_names,
                'data': np.column_stack((kps_linearized, E))
        }
    elif ISPIN == 2:
        E_spin1 -= Ef
        E_spin2 -= Ef
        # plot the bands of up and down overlapped
        plot_helper_figs(on_figs)
        ax = plt.subplot(111)
        for band in range(N_bands):
            plt.plot(kps_linearized, E_spin1[:, band], 'k', label='spin up')
            plt.plot(kps_linearized, E_spin2[:, band], 'b', label='spin down')
        plot_helper_settings(ax, axis_range, reciprocal_point_locations, reciprocal_points,
                             save_figs, output_prefix+'-overlapped.pdf')
        axes = {'ax': ax}
        return_dict['spin_up_data'] = {
                'columns': col_names1,
                'data': np.column_stack((kps_linearized, E_spin1))
            }
        return_dict['spin_down_data'] = {
                'columns': col_names2,
                'data': np.column_stack((kps_linearized, E_spin2))
            }

    if display:
        plt.show()
    if close_figs:
        plt.close('all')
    else:
        return_dict['axes'] = axes
    return return_dict
