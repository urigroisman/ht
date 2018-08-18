# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2016, Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

from __future__ import division
from math import pi, sin, acos, radians
from scipy.constants import g
from scipy.interpolate import  UnivariateSpline, interp2d, RectBivariateSpline
import numpy as np
from ht.core import wall_factor, WALL_FACTOR_PRANDTL

__all__ = ['dP_Kern', 'Kern_f_Re', 'dP_Zukauskas', 'dP_staggered_f',
           'dP_staggered_correction', 'dP_inline_f', 'dP_inline_correction',
           'Nu_ESDU_73031', 'Nu_Zukauskas_Bejan','Nu_HEDH_tube_bank',
           'Nu_Grimison_tube_bank',
           'Zukauskas_tube_row_correction', 
           'ESDU_tube_row_correction',
           'ESDU_tube_angle_correction',
	   'baffle_correction_Bell', 'baffle_leakage_Bell',
           'bundle_bypassing_Bell']


# Applies for row 1-9.
Grimson_Nl_aligned = [0.64, 0.8, 0.87, 0.9, 0.92, 0.94, 0.96, 0.98, 0.99]
Grimson_Nl_staggered = [0.68, 0.75, 0.83, 0.89, 0.92, 0.95, 0.97, 0.98, 0.99]


Grimison_SL_aligned = np.array([1.25, 1.5, 2, 3])
Grimison_ST_aligned = Grimison_SL_aligned
Grimison_C1_aligned = np.array([[0.348, 0.275, 0.1, 0.0633],
                                [0.367, 0.25, 0.101, 0.0678],
                                [0.418, 0.299, 0.229, 0.198],
                                [0.29, 0.357, 0.374, 0.286]])
Grimison_m_aligned = np.array([[0.592, 0.608, 0.704, 0.752],
                               [0.586, 0.62, 0.702, 0.744],
                               [0.57, 0.602, 0.632, 0.648],
                               [0.601, 0.584, 0.581, 0.608]])

Grimison_C1_aligned_interp = RectBivariateSpline(Grimison_ST_aligned, 
                                                 Grimison_SL_aligned,
                                                 Grimison_C1_aligned)
Grimison_m_aligned_interp = RectBivariateSpline(Grimison_ST_aligned, 
                                                Grimison_SL_aligned, 
                                                Grimison_m_aligned)

Grimson_SL_staggered = np.array([1.25, 1.5, 2, 3, 1, 1.25, 1.5, 2, 3, 0.9, 
                                 1.125, 1.25, 1.5, 2, 3, 0.6, 0.9, 1.125, 1.25,
                                 1.5, 2, 3])

Grimson_ST_staggered = np.array([1.25, 1.25, 1.25, 1.25, 1.5, 1.5, 1.5, 1.5, 
                                 1.5, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3])

Grimson_m_staggered = np.array([0.556, 0.568, 0.572, 0.592, 0.558, 0.554, 
                                0.562, 0.568, 0.58, 0.571, 0.565, 0.556, 0.568,
                                0.556, 0.562, 0.636, 0.581, 0.56, 0.562, 0.568,
                                0.57, 0.574])

Grimson_C1_staggered = np.array([0.518, 0.451, 0.404, 0.31, 0.497, 0.505, 0.46,
                                 0.416, 0.356, 0.446, 0.478, 0.519, 0.452,
                                 0.482, 0.44, 0.213, 0.401, 0.518, 0.522, 
                                 0.488, 0.449, 0.428])

Grimson_m_staggered_interp = interp2d(Grimson_ST_staggered,
                                      Grimson_SL_staggered, 
                                      Grimson_m_staggered, kind='linear')
Grimson_C1_staggered_interp = interp2d(Grimson_ST_staggered, 
                                       Grimson_SL_staggered, 
                                       Grimson_C1_staggered, kind='linear')


def Nu_Grimison_tube_bank(Re, Pr, Do, tube_rows, pitch_parallel, pitch_normal):
    r'''Calculates Nusselt number for crossflow across a tube bank
    of tube rows at a specified `Re`, `Pr`, and `D` using the Grimison 
    methodology as described in [1]_.

    .. math::
        \bar{Nu_D} = 1.13C_1Re_{D,max}^m Pr^{1/3}C_2

    Parameters
    ----------
    Re : float
        Reynolds number with respect to average (bulk) fluid properties and
        tube outside diameter, [-]
    Pr : float
        Prandtl number with respect to average (bulk) fluid properties, [-]
    Do : float
        Tube outer diameter, [m]
    tube_rows : int
        Number of tube rows per bundle, [-]
    pitch_parallel : float
        Distance between tube center along a line parallel to the flow;
        has been called `longitudinal` pitch, `pp`, `s2`, `SL`, and `p2`, [m]
    pitch_normal : float
        Distance between tube centers in a line 90° to the line of flow;
        has been called the `transverse` pitch, `pn`, `s1`, `ST`, and `p1`, [m]
    
    Returns
    -------
    Nu : float
        Nusselt number with respect to tube outside diameter, [-]

    Notes
    -----
    Tube row correction factors are applied for tube row counts less than 10,
    also published in [1]_.

    Examples
    --------
    >>> Nu_Grimison_tube_bank(Re=10263.37, Pr=.708, tube_rows=11, 
    ... pitch_normal=.05, pitch_parallel=.05, Do=.025)
    79.07883866010096

    >>> Nu_Grimison_tube_bank(Re=10263.37, Pr=.708, tube_rows=11, 
    ... pitch_normal=.07, pitch_parallel=.05, Do=.025)
    79.92721078571385

    References
    ----------
    .. [1] Grimson, E. D. (1937) Correlation and Utilisation of New Data on
       Flow Resistance and Heat Transfer for Cross Flow of Gases over Tube 
       Banks. Trans. ASME. 59 583-594
    '''
    staggered = abs(1 - pitch_normal/pitch_parallel) > 0.05
    a = pitch_normal/Do # sT
    b = pitch_parallel/Do
    if not staggered:
        C1 = float(Grimison_C1_aligned_interp(b, a))
        m = float(Grimison_m_aligned_interp(b, a))
    else:
        C1 = float(Grimson_C1_staggered_interp(b, a))
        m = float(Grimson_m_staggered_interp(b, a))
        
    tube_rows = int(tube_rows)
    if tube_rows < 10:
        if tube_rows < 1:
            tube_rows = 1
        if staggered:
            C2 = Grimson_Nl_staggered[tube_rows]
        else:
            C2 = Grimson_Nl_aligned[tube_rows]
    else:
        C2 = 1.0
    Nu = 1.13*Re**m*Pr**(1.0/3.0)*C2*C1
    return Nu


Zukauskas_Czs_low_Re_staggered = [0.8295, 0.8792, 0.9151, 0.9402, 0.957, 0.9677,
    0.9745, 0.9785, 0.9808, 0.9823, 0.9838, 0.9855, 0.9873, 0.9891, 0.991,
    0.9929, 0.9948, 0.9967, 0.9987]
Zukauskas_Czs_high_Re_staggered = [0.6273, 0.7689, 0.8473, 0.8942, 0.9254,
    0.945, 0.957, 0.9652, 0.9716, 0.9765, 0.9803, 0.9834, 0.9862, 0.989,
    0.9918, 0.9943, 0.9965, 0.998, 0.9986]
Zukauskas_Czs_inline = [0.6768, 0.8089, 0.8687, 0.9054, 0.9303, 0.9465, 0.9569,
    0.9647, 0.9712, 0.9766, 0.9811, 0.9847, 0.9877, 0.99, 0.992, 0.9937,
    0.9953, 0.9969, 0.9986]

def Zukauskas_tube_row_correction(tube_rows, staggered=True, Re=1E4):
    r'''Calculates the tube row correction factor according to a graph
    digitized from [1]_ and also shown in [2]_ for heat transfer across
    a tube bundle. The correction factors are slightly different for 
    staggered vs. inline configurations; for the staggered configuration,
    factors are avaliable separately for `Re` larger or smaller than 1000.
    
    This method is a tabular lookup, with values of 1 when the tube row count
    is 20 or more.
    
    Parameters
    ----------
    tube_rows : int
        Number of tube rows per bundle, [-]
    staggered : bool, optional
        Whether in the in-line or staggered configuration, [-]
    Re : float, optional
        The Reynolds number of flow through the tube bank using the bare tube
        outer diameter and the minimum flow area through the bundle, [-]
        
    Returns
    -------
    F : float
        Tube row count correction factor, [-]

    Notes
    -----
    The basis for this method is that an infinitely long tube bank has a 
    factor of 1; in practice the factor is reached at 20 rows.
    
    Examples
    --------
    >>> Zukauskas_tube_row_correction(4, staggered=True)
    0.8942
    >>> Zukauskas_tube_row_correction(6, staggered=False)
    0.9465

    References
    ----------
    .. [1] Zukauskas, A. Heat transfer from tubes in crossflow. In T.F. Irvine,
       Jr. and J. P. Hartnett, editors, Advances in Heat Transfer, volume 8,
       pages 93-160. Academic Press, Inc., New York, 1972.
    '''
    tube_rows = int(tube_rows) # sanity for indexing
    if tube_rows < 1:
        tube_rows = 1
    if staggered: # in-line, with a tolerance of 0.05 proximity
        if tube_rows <= 19:
            factors = Zukauskas_Czs_low_Re_staggered if Re < 1000 else Zukauskas_Czs_high_Re_staggered
            correction = factors[tube_rows-1]
        else:
            correction = 1.0
    else:
        if tube_rows <= 19:
            correction = Zukauskas_Czs_inline[tube_rows-1]
        else:
            correction = 1.0
    return correction


def Nu_Zukauskas_Bejan(Re, Pr, tube_rows, pitch_parallel, pitch_normal,
                       Pr_wall=None):
    r'''Calculates Nusselt number for crossflow across a tube bank
    of tube number n at a specified `Re` according to the method of Zukauskas 
    [1]_. A fit to graphs from [1]_ published in [2]_ is used for the 
    correlation. The tube row correction factor is obtained from digitized 
    graphs from [1]_, and a lookup table was created and is used for speed.

    The formulas are as follows:

    Aligned tube banks:

    .. math::
        \bar Nu_D = 0.9 C_nRe_D^{0.4}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 1 < Re < 100

    .. math::
        \bar Nu_D = 0.52 C_nRe_D^{0.5}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 100 < Re < 1000

    .. math::
        \bar Nu_D = 0.27 C_nRe_D^{0.63}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 1000 < Re < 20000

    .. math::
        \bar Nu_D = 0.033 C_nRe_D^{0.8}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 20000 < Re < 200000

    Staggered tube banks:

    .. math::
        \bar Nu_D = 1.04C_nRe_D^{0.4}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 1 < Re < 500

    .. math::
        \bar Nu_D = 0.71C_nRe_D^{0.5}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \text{ for } 500 < Re < 1000

    .. math::
        \bar Nu_D = 0.35 C_nRe_D^{0.6}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \left(\frac{X_t}{X_l}\right)^{0.2}
        \text{ for } 1000 < Re < 20000

    .. math::
        \bar Nu_D = 0.031 C_nRe_D^{0.8}Pr^{0.36}\left(\frac{Pr}{Pr_w}\right)^{0.25}
        \left(\frac{X_t}{X_l}\right)^{0.2}
        \text{ for } 20000 < Re < 200000

    Parameters
    ----------
    Re : float
        Reynolds number with respect to average (bulk) fluid properties and
        tube outside diameter, [-]
    Pr : float
        Prandtl number with respect to average (bulk) fluid properties, [-]
    tube_rows : int
        Number of tube rows per bundle, [-]
    pitch_parallel : float
        Distance between tube center along a line parallel to the flow;
        has been called `longitudinal` pitch, `pp`, `s2`, `SL`, and `p2`, [m]
    pitch_normal : float
        Distance between tube centers in a line 90° to the line of flow;
        has been called the `transverse` pitch, `pn`, `s1`, `ST`, and `p1`, [m]
    Pr_wall : float, optional
        Prandtl number at the wall temperature; provide if a correction with  
        the defaults parameters is desired; otherwise apply the correction
        elsewhere, [-]

    Returns
    -------
    Nu : float
        Nusselt number with respect to tube outside diameter, [-]

    Notes
    -----
    If `Pr_wall` is not provided, the Prandtl number correction
    is not used and left to an outside function.  A Prandtl number exponent of
    0.25 is recommended in [1]_ for heating and cooling for both liquids and
    gases.

    Examples
    --------
    >>> Nu_Zukauskas_Bejan(Re=1E4, Pr=7., tube_rows=10, pitch_parallel=.05, pitch_normal=.05)
    175.9202277145248

    References
    ----------
    .. [1] Zukauskas, A. Heat transfer from tubes in crossflow. In T.F. Irvine,
       Jr. and J. P. Hartnett, editors, Advances in Heat Transfer, volume 8,
       pages 93-160. Academic Press, Inc., New York, 1972.
    .. [2] Bejan, Adrian. "Convection Heat Transfer", 4E. Hoboken,
       New Jersey: Wiley, 2013.
    '''
    staggered = abs(1 - pitch_normal/pitch_parallel) > 0.05

    f = 1.0
    if not staggered:
        if Re < 100:
            c, m = 0.9, 0.4
        elif Re < 1000:
            c, m = 0.52, 0.05
        elif Re < 2E5:
            c, m = 0.27, 0.63
        else:
            c, m = 0.033, 0.8
    else:
        if Re < 500:
            c, m = 1.04, 0.4
        elif Re < 1000:
            c, m = 0.71, 0.5
        elif Re < 2E5:
            c, m = 0.35, 0.6
            f = (pitch_normal/pitch_parallel)**0.2
        else:
            c, m = 0.031, 0.8
            f = (pitch_normal/pitch_parallel)**0.2
    
    Nu = c*Re**m*Pr**0.36*f
    if Pr_wall is not None:
        Nu*= (Pr/Pr_wall)**0.25
    Cn = Zukauskas_tube_row_correction(tube_rows, staggered=staggered, Re=Re)
    Nu *= Cn
    return Nu


# For row counts 3 to 9, inclusive. Lower tube counts shouldn't be considered
# tube banks. 10 is 1.
ESDU_73031_F2_inline = [0.8479, 0.8957, 0.9306, 0.9551, 0.9724, 0.9839, 0.9902]
ESDU_73031_F2_staggered = [0.8593, 0.8984, 0.9268, 0.9482, 0.965, 0.9777, 0.9868]

def ESDU_tube_row_correction(tube_rows, staggered=True, Re=3000, method='Hewitt'):
    r'''Calculates the tube row correction factor according to [1]_ as shown in
    [2]_ for heat transfer across a tube bundle. This is also used for finned 
    bundles. The correction factors are slightly different for staggered vs. 
    inline configurations.
    
    This method is a tabular lookup, with values of 1 when the tube row count
    is 10 or more.
    
    Parameters
    ----------
    tube_rows : int
        Number of tube rows per bundle, [-]
    staggered : bool, optional
        Whether in the in-line or staggered configuration, [-]
    Re : float, optional
        The Reynolds number of flow through the tube bank using the bare tube
        outer diameter and the minimum flow area through the bundle, [-]
    method : str, optional
        'Hewitt'; this may have another option in the future, [-]
        
    Returns
    -------
    F2 : float
        ESDU tube row count correction factor, [-]

    Notes
    -----
    In [1]_, for line data, there are two curves given for different Reynolds
    number ranges. This is not included in [2]_ and only an average curve is 
    given. This is not implemented here; `Re` is an argument but does not
    impact the result of this function.
    
    For tube counts 1-7, [3]_ claims the factors from [1]_ are on average:
    [0.65, 0.77, 0.84, 0.9, 0.94, 0.97, 0.99].
    
    Examples
    --------
    >>> ESDU_tube_row_correction(4, staggered=True)
    0.8984
    >>> ESDU_tube_row_correction(6, staggered=False)
    0.9551

    References
    ----------
    .. [1] "Convective Heat Transfer During Crossflow of Fluids Over Plain Tube 
       Banks." ESDU 73031 (November 1, 1973). 
    .. [2] Hewitt, G. L. Shires, T. Reg Bott G. F., George L. Shires, and T.
       R. Bott. Process Heat Transfer. 1st edition. Boca Raton: CRC Press, 
       1994.
    .. [3] Rabas, T. J., and J. Taborek. "Survey of Turbulent Forced-Convection
       Heat Transfer and Pressure Drop Characteristics of Low-Finned Tube Banks
       in Cross Flow."  Heat Transfer Engineering 8, no. 2 (January 1987): 
       49-62.
    '''
    if method == 'Hewitt':
        if staggered: # in-line, with a tolerance of 0.05 proximity
            if tube_rows <= 2:
                correction = ESDU_73031_F2_staggered[0]
            elif tube_rows >= 10:
                correction = 1.0
            else:
                correction = ESDU_73031_F2_staggered[tube_rows-3]
        else:
            if tube_rows <= 2:
                correction = ESDU_73031_F2_inline[0]
            elif tube_rows >= 10:
                correction = 1.0
            else:
                correction = ESDU_73031_F2_inline[tube_rows-3]
        return correction


def ESDU_tube_angle_correction(angle):
    r'''Calculates the tube bank inclination correction factor according to 
    [1]_ for heat transfer across a tube bundle. 

    .. math::
        F_3 = \frac{Nu_{\theta}}{Nu_{\theta=90^{\circ}}} = (\sin(\theta))^{0.6}
    
    Parameters
    ----------
    angle : float
        The angle of inclination of the tuba bank with respect to the 
        longitudinal axis (90° for a straight tube bank)
        
    Returns
    -------
    F3 : float
        ESDU tube inclination correction factor, [-]

    Notes
    -----
    A curve is given in [1]_ but it is so close the function, it is likely the
    function is all that is used. [1]_ claims this correction is valid for
    :math:`100 < Re < 10^{6}`.
    
    For angles less than 10°, the problem should be considered internal
    flow, not flow across a tube bank.
    
    Examples
    --------
    >>> ESDU_tube_angle_correction(75)
    0.9794139080247666

    References
    ----------
    .. [1] "Convective Heat Transfer During Crossflow of Fluids Over Plain Tube 
       Banks." ESDU 73031 (November 1, 1973). 
    '''
    return sin(radians(angle))**0.6


def Nu_ESDU_73031(Re, Pr, tube_rows, pitch_parallel, pitch_normal, 
                  Pr_wall=None, angle=90.0):
    r'''Calculates the Nusselt number for crossflow across a tube bank
    with a specified number of tube rows, at a specified `Re` according to 
    [1]_, also shown in [2]_.
    
    .. math::
        \text{Nu} = a \text{Re}^m\text{Pr}^{0.34}F_1 F_2

    The constants `a` and `m` come from the following tables:
    
    In-line tube banks:

    +---------+-------+-------+
    | Re      | a     | m     |
    +=========+=======+=======+
    | 10-300  | 0.742 | 0.431 |
    +---------+-------+-------+
    | 300-2E5 | 0.211 | 0.651 |
    +---------+-------+-------+
    | 2E5-2E6 | 0.116 | 0.700 |
    +---------+-------+-------+
    
    Staggered tube banks:
        
    +---------+-------+-------+
    | Re      | a     | m     |
    +=========+=======+=======+
    | 10-300  | 1.309 | 0.360 |
    +---------+-------+-------+
    | 300-2E5 | 0.273 | 0.635 |
    +---------+-------+-------+
    | 2E5-2E6 | 0.124 | 0.700 |
    +---------+-------+-------+

    Parameters
    ----------
    Re : float
        Reynolds number with respect to average (bulk) fluid properties and
        tube outside diameter, [-]
    Pr : float
        Prandtl number with respect to average (bulk) fluid properties, [-]
    tube_rows : int
        Number of tube rows per bundle, [-]
    pitch_parallel : float
        Distance between tube center along a line parallel to the flow;
        has been called `longitudinal` pitch, `pp`, `s2`, `SL`, and `p2`, [m]
    pitch_normal : float
        Distance between tube centers in a line 90° to the line of flow;
        has been called the `transverse` pitch, `pn`, `s1`, `ST`, and `p1`, [m]
    Pr_wall : float, optional
        Prandtl number at the wall temperature; provide if a correction with  
        the defaults parameters is desired; otherwise apply the correction
        elsewhere, [-]
    angle : float, optional
        The angle of inclination of the tuba bank with respect to the 
        longitudinal axis (90° for a straight tube bank)

    Returns
    -------
    Nu : float
        Nusselt number with respect to tube outside diameter, [-]

    Notes
    -----
    The tube-row count correction factor `F2` can be disabled by setting `tube_rows`
    to 10. The property correction factor `F1` can be disabled by not specifiying
    `Pr_wall`. A Prandtl number exponent of 0.26 is recommended in [1]_ for 
    heating and cooling for both liquids and gases.

    The pitches are used to determine whhether or not to use data for staggered
    or inline tube banks.
    
    The inline coefficients are valid for a normal pitch to tube diameter ratio
    from 1.2 to 4; and the staggered ones from 1 to 4. 
    The overall accuracy of this method is claimed to be 15%.
    
    See Also
    --------
    ESDU_tube_angle_correction
    ESDU_tube_row_correction
    
    Examples
    --------
    >>> Nu_ESDU_73031(Re=1.32E4, Pr=0.71, tube_rows=8, pitch_parallel=.09, 
    ... pitch_normal=.05)
    98.2563319140594

    References
    ----------
    .. [1] "High-Fin Staggered Tube Banks: Heat Transfer and Pressure Drop for
       Turbulent Single Phase Gas Flow." ESDU 86022 (October 1, 1986). 
    .. [2] Hewitt, G. L. Shires, T. Reg Bott G. F., George L. Shires, and T.
       R. Bott. Process Heat Transfer. 1st edition. Boca Raton: CRC Press, 
       1994.
    '''
    staggered = abs(1 - pitch_normal/pitch_parallel) > 0.05
    if staggered:
        if Re <= 300:
            a, m = 1.309, 0.360
        elif Re <= 2E5:
            a, m = 0.273, 0.635
        else:
            a, m = 0.124, 0.700
    else:
        if Re <= 300:
            a, m = 0.742, 0.431
        elif Re <= 2E5:
            a, m = 0.211, 0.651
        else:
            a, m = 0.116, 0.700
    
    F2 = ESDU_tube_row_correction(tube_rows=tube_rows, staggered=staggered)
    F3 = ESDU_tube_angle_correction(angle)
    if Pr_wall is not None:
        F1 = wall_factor(Pr=Pr, Pr_wall=Pr_wall, Pr_heating_coeff=0.26, 
                         Pr_cooling_coeff=0.26, 
                         property_option=WALL_FACTOR_PRANDTL)
    else:
        F1 = 1.0
    return a*Re**m*Pr**0.34*F1*F2*F3


def Nu_HEDH_tube_bank(Re, Pr, Do, tube_rows, pitch_parallel, pitch_normal):
    r'''Calculates Nusselt number for crossflow across a tube bank
    of tube rows at a specified `Re`, `Pr`, and `D` using the Heat Exchanger
    Design Handbook (HEDH) methodology, presented in [1]_.

    .. math::
        Nu = Nu_m f_A f_N

    .. math::
        Nu_m = 0.3 + \sqrt{Nu_{m,lam}^2 + Nu_{m,turb}^2}

    .. math::
        Nu_{m,turb} = \frac{0.037Re^{0.8} Pr}{1 + 2.443Re^{-0.1}(Pr^{2/3} -1)}

    .. math::
        Nu_{m,lam} = 0.664Re^{0.5} Pr^{1/3}

    .. math::
        \psi = 1 - \frac{\pi}{4a} \text{ if b >= 1}

    .. math::
        \psi = 1 - \frac{\pi}{4ab} \text{if b < 1}

    .. math::
        f_A = 1 + \frac{0.7}{\psi^{1.5}}\frac{b/a-0.3}{(b/a) + 0.7)^2} \text{if inline}

    .. math::
        f_A = 1 + \frac{2}{3b} \text{elif partly staggered}

    .. math::
        f_N = \frac{1 + (n-1)}{n}

    Parameters
    ----------
    Re : float
        Reynolds number with respect to average (bulk) fluid properties and
        tube outside diameter, [-]
    Pr : float
        Prandtl number with respect to average (bulk) fluid properties, [-]
    Do : float
        Tube outer diameter, [m]
    tube_rows : int
        Number of tube rows per bundle, [-]
    pitch_parallel : float
        Distance between tube center along a line parallel to the flow;
        has been called `longitudinal` pitch, `pp`, `s2`, `SL`, and `p2`, [m]
    pitch_normal : float
        Distance between tube centers in a line 90° to the line of flow;
        has been called the `transverse` pitch, `pn`, `s1`, `ST`, and `p1`, [m]

    Returns
    -------
    Nu : float
        Nusselt number with respect to tube outside diameter, [-]

    Notes
    -----
    Prandtl number correction left to an outside function, although a set
    of coefficients were specified in [1]_ because they depent on whether 
    heating or cooling is happening, and for gases, use a temperature ratio
    instaed of Prandtl number.

    The claimed range of validity of these expressions is :math:`10 < Re < 1E5`
    and :math:`0.6 < Pr < 1000`.

    Examples
    --------
    >>> Nu_HEDH_tube_bank(Re=1E4, Pr=7., tube_rows=10, pitch_normal=.05, 
    ... pitch_parallel=.05, Do=.03)
    382.4636554404698
    
    Example 3.11 in [2]_:
    
    >>> Nu_HEDH_tube_bank(Re=10263.37, Pr=.708, tube_rows=11, pitch_normal=.05, 
    ... pitch_parallel=.05, Do=.025)
    149.18735251017594

    References
    ----------
    .. [1] Schlunder, Ernst U, and International Center for Heat and Mass
       Transfer. Heat Exchanger Design Handbook. Washington:
       Hemisphere Pub. Corp., 1987.
    .. [2] Baehr, Hans Dieter, and Karl Stephan. Heat and Mass Transfer.
       Springer, 2013.
    '''
    staggered = abs(1 - pitch_normal/pitch_parallel) > 0.05
    a = pitch_normal/Do
    b = pitch_parallel/Do
    if b >= 1:
        voidage = 1. - pi/(4.0*a)
    else:
        voidage = 1. - pi/(4.0*a*b)
    Re = Re/voidage
    Nu_laminar = 0.664*Re**0.5*Pr**(1.0/3.)
    Nu_turbulent = 0.037*Re**0.8*Pr/(1. + 2.443*Re**-0.1*(Pr**(2/3.) - 1.0))
    Nu = 0.3 + (Nu_laminar*Nu_laminar + Nu_turbulent*Nu_turbulent)**0.5
    if not staggered:
        fA = 1.0 + 0.7/voidage**1.5*(b/a - 0.3)/(b/a + 0.7)**2
    else:
        fA = 1.0 + 2./(3.0*b)
        # a further partly staggered tube bank correlation exists, using another pitch
    if tube_rows < 10:
        fn = (1.0 + (n - 1.0))/tube_rows
    else:
        fn = 1.0
    Nu = Nu*fn*fA
    return Nu

_Kern_dP_Res = np.array([9.9524, 11.0349, 12.0786, 13.0504, 14.0121, 15.0431, 16.1511, 17.1176, 17.9105, 18.9822,
    19.9879, 21.0484, 22.0217, 23.1893, 24.8973, 26.0495, 27.7862, 29.835, 31.8252, 33.9506, 35.9822, 38.3852,
    41.481, 43.9664, 47.2083, 50.6891, 54.0782, 58.0635, 63.5667, 68.2537, 74.247, 78.6957, 83.9573, 90.1511,
    95.5596, 102.613, 110.191, 116.806, 128.724, 137.345, 150.384, 161.484, 171.185, 185.031, 196.139, 210.639,
    230.653, 250.933, 281.996, 300.884, 329.472, 353.842, 384.968, 408.108, 444.008, 505.513, 560.821, 638.506,
    690.227, 741.254, 827.682, 918.205, 1018.63, 1122.76, 1213.62, 1320.38, 1417.94, 1522.93, 1667.69, 1838.11,
    2012.76, 2247.44, 2592.21, 2932.18, 3381.87, 3875.42, 4440.83, 5056.16, 5608.95, 6344.58, 7038.48, 8224.34,
    9123.83, 10121.7, 11598, 12701.4, 14090, 15938.5, 17452.9, 19112.6, 20929.3, 24614, 29324.6, 34044.8,
    37282.2, 42999.9, 50570.2, 55737.9, 59860.6, 65553, 70399.2, 78101.5, 84965.7, 96735.3, 110139, 122977,
    136431, 152339, 165740, 180319, 194904, 207981, 223357, 241440, 257621, 283946, 317042, 353996, 408315,
    452956, 519041, 590939, 668466, 751216, 827981, 894985, 1012440
])
_Kern_dP_fs = 144.0 * np.array([0.0429177, 0.0382731, 0.0347901, 0.0316208, 0.0298653, 0.0276702, 0.0259671, 0.024523,
    0.0237582, 0.0224369, 0.0211881, 0.0202668, 0.0193847, 0.0184234, 0.0172894, 0.0166432, 0.0155182,
    0.0147509, 0.0138423, 0.0131572, 0.0124255, 0.0118105, 0.0110842, 0.0106028, 0.0100785, 0.00958019,
    0.0092235, 0.00871144, 0.00817649, 0.0077722, 0.00743616, 0.0071132, 0.00684836, 0.00655159, 0.00634789,
    0.00611185, 0.00592242, 0.00577517, 0.00552603, 0.00542355, 0.00522267, 0.00502847, 0.00493497, 0.00481301,
    0.00469334, 0.00460654, 0.00449314, 0.00438231, 0.00424799, 0.00416922, 0.00406658, 0.00401703, 0.00394314,
    0.0038947, 0.00382305, 0.00373007, 0.00368555, 0.00359592, 0.00357512, 0.003509, 0.00344515, 0.00338229,
    0.00332057, 0.00328077, 0.00322026, 0.00316102, 0.00308274, 0.00308446, 0.00302787, 0.00297247, 0.0028993,
    0.00284654, 0.00277759, 0.0027099, 0.00262738, 0.00256361, 0.00248541, 0.00244055, 0.00238072, 0.0023227,
    0.00228032, 0.00222531, 0.00218471, 0.00214484, 0.00206613, 0.00205439, 0.00200402, 0.00196775, 0.00191932,
    0.00189622, 0.00186143, 0.00180501, 0.0017393, 0.00170817, 0.00168761, 0.00163622, 0.00158663, 0.0015576,
    0.00153862, 0.0015201, 0.00149199, 0.00147418, 0.00142864, 0.00139389, 0.00136874, 0.00133524, 0.00131931,
    0.0012953, 0.00127147, 0.00124808, 0.00121724, 0.00121785, 0.00119533, 0.00118082, 0.00116638, 0.00114504,
    0.00111702, 0.00108969, 0.00107013, 0.00104389, 0.00101205, 0.000987437, 0.000969567, 0.000939849,
    0.000922653, 0.000905634, 0.000894962
])
# Used in preference over interp1d as saves 30% of execution time, and
# performs some marginally small amount of smoothing
# s=0.1 is chosen to have 9 knots, a reasonable amount.
Kern_f_Re = UnivariateSpline(_Kern_dP_Res, _Kern_dP_fs, s=0.1)

# Graph presented in Peters and Timmerhaus uses fanning friction factor.
# This uses Darcy's friction factor.


def dP_Kern(m, rho, mu, DShell, LSpacing, pitch, Do, NBaffles, mu_w=None):
    r'''Calculates pressure drop for crossflow across a tube bank
    according to the equivalent-diameter method developed by Kern [1]_,
    presented in [2]_.

    .. math::
        \Delta P = \frac{f (m/S_s)^2 D_s(N_B+1)}{2\rho D_e(\mu/\mu_w)^{0.14}}

        S_S = \frac{D_S (P_T-D_o) L_B}{P_T}

        D_e = \frac{4(P_T^2 - \pi D_o^2/4)}{\pi D_o}

    Parameters
    ----------
    m : float
        Mass flow rate, [kg/s]
    rho : float
        Fluid density, [kg/m^3]
    mu : float
        Fluid viscosity, [Pa*s]
    DShell : float
        Diameter of exchanger shell, [m]
    LSpacing : float
        Baffle spacing, [m]
    pitch : float
        Tube pitch, [m]
    Do : float
        Tube outer diameter, [m]
    NBaffles : float
        Baffle count, []
    mu_w : float
        Fluid viscosity at wall temperature, [Pa*s]

    Returns
    -------
    dP : float
        Pressure drop across bundle, [Pa]

    Notes
    -----
    Adjustment for viscosity left out of this function.
    Example is from [2]_. Roughly 10% difference due to reading of graph.
    Graph scanned from [1]_, and interpolation is used to read it.

    Examples
    --------
    >>> dP_Kern(m=11., rho=995., mu=0.000803, mu_w=0.000657, DShell=0.584,
    ... LSpacing=0.1524, pitch=0.0254, Do=.019, NBaffles=22)
    18980.58768759033

    References
    ----------
    .. [1] Kern, Donald Quentin. Process Heat Transfer. McGraw-Hill, 1950.
    .. [2] Peters, Max, Klaus Timmerhaus, and Ronald West. Plant Design and
       Economics for Chemical Engineers. 5E. New York: McGraw-Hill, 2002.
    '''
    # Adjustment for viscosity performed if given
    Ss = DShell*(pitch-Do)*LSpacing/pitch
    De = 4*(pitch**2 - pi*Do**2/4.)/pi/Do
    Vs = m/Ss/rho
    Re = rho*De*Vs/mu
    f = float(Kern_f_Re(Re))
    if mu_w:
        return f*(Vs*rho)**2*DShell*(NBaffles+1)/(2*rho*De*(mu/mu_w)**0.14)
    else:
        return f*(Vs*rho)**2*DShell*(NBaffles+1)/(2*rho*De)



_dP_staggered_Res = np.array([10, 10.9129, 11.6733, 13.1024, 14.0153, 14.9918, 17.1536, 18.5267, 19.8182, 20.7261, 22.243, 23.7936, 26.7057, 28.5663, 32.2732,
    34.858, 37.2879, 41.0554, 44.4722, 47.8949, 51.2337, 55.3369, 65.1821, 70.4025, 76.0437, 82.1368, 88.7182, 95.1284, 100.553, 103.386, 108.398,
    116.441, 118.455, 127.808, 129.188, 139.389, 140.899, 153.665, 155.444, 167.595, 168.914, 182.793, 197.771, 201.613, 217.768, 223.559, 241.759,
    246.457, 268.516, 278.915, 292.866, 304.208, 322.535, 335.015, 351.772, 366.482, 402.412, 415.414, 451.79, 465.314, 497.559, 512.453, 542.68,
    570.321, 609.312, 610.163, 671.039, 671.953, 731.917, 732.915, 813.886, 839.919, 896.808, 977.69, 1016.19, 1119.14, 1221.31, 1244.48, 1346.07,
    1455.66, 1482.44, 1603.12, 1616.93, 1748.56, 1780.79, 1925.77, 1961.27, 2056.71, 2060.37, 2266.81, 2308.27, 2474.96, 2542.2, 2723.03, 2799.84,
    2996.9, 3053.95, 3274.27, 3363.57, 3606.09, 4001.84, 4005.75, 4367.03, 4411.71, 4809.6, 4854.24, 5297.21, 5346.19, 5777.99, 5836.5, 6184.44,
    6739.62, 6817.15, 7422.65, 7435.62, 8188.61, 8256.81, 9005.89, 9089.79, 9914.09, 9931.42, 10832, 11357.6, 11913.2, 12508.2, 13011.2, 13642.4,
    14309.8, 15024.5, 15759.5, 16387, 17188.6, 18046.5, 18772.3, 19683.7, 20458.2, 22313.4, 22950.8, 24573.9, 26311.7, 27049.2, 28976.2, 29516.6, 31605,
    32505.6, 34805.6, 35453.4, 37961.9, 39045, 39838.4, 40171.7, 43802.4, 43836, 47853, 48253.3, 52629.1, 57429.8, 57958.7, 60823.7, 63808, 66429.9,
    72454.1, 76644.8, 79791.3, 86914.7, 87727.5, 94796.5, 95846.9, 102543, 103393, 112734, 123172, 124193, 134342, 136770, 147946, 149173, 161368,
    162701, 177710, 179183, 193825, 197329, 203406, 205093, 224028, 225878, 246499, 248787, 268891, 271756, 296172, 299307, 323098, 329652, 355768,
    363073, 388139, 399883, 411321, 411637, 453053, 453370, 494224, 499159, 539099, 549766, 593776, 617117, 617548, 679896, 741914, 748826, 816818,
    899347, 899975, 991217, 1029890, 1039630, 1134310, 1145030, 1249310, 1261120, 1375630, 1388740, 1515150, 1529530, 1668760, 1684660, 1837940,
    1855450, 2063320, 2064190, 2251140, 2273460, 2479450, 2502990, 2730830, 2756750
])
_dP_staggered_Re_125 = np.array([23.9929, 22.6513, 21.1808, 19.0604, 17.8231, 16.6661, 14.5725, 13.6264, 12.8644, 12.1931, 11.3569, 10.7219, 9.55649, 8.93611,
    7.91304, 7.32822, 6.89654, 6.28568, 5.80434, 5.44301, 5.08949, 4.72306, 4.06698, 3.79555, 3.5683, 3.30447, 3.1177, 2.91006, 2.77913, 2.71412,
    2.60635, 2.4487, 2.41753, 2.2802, 2.25939, 2.12672, 2.11005, 1.98054, 1.96397, 1.85661, 1.84576, 1.74274, 1.66846, 1.63677, 1.56011, 1.53763,
    1.47248, 1.45689, 1.38943, 1.36053, 1.32959, 1.30743, 1.27402, 1.2528, 1.22604, 1.20401, 1.15477, 1.13664, 1.10541, 1.09271, 1.06394, 1.05209,
    1.02957, 1.01043, 0.985509, 0.984989, 0.950966, 0.950537, 0.92446, 0.924083, 0.894818, 0.885516, 0.868347, 0.848317, 0.840024, 0.819658, 0.801646,
    0.797824, 0.782058, 0.766644, 0.763863, 0.752037, 0.75061, 0.737713, 0.736366, 0.730623, 0.728723, 0.723802, 0.723618, 0.709974, 0.707146, 0.696311,
    0.694446, 0.689689, 0.685538, 0.675409, 0.672874, 0.663594, 0.66181, 0.657217, 0.636046, 0.63585, 0.619904, 0.619273, 0.613337, 0.612083, 0.601667,
    0.601114, 0.595116, 0.592882, 0.580202, 0.570252, 0.568954, 0.558333, 0.558117, 0.542262, 0.541366, 0.532074, 0.530674, 0.517089, 0.516819,
    0.502141, 0.497421, 0.492707, 0.484889, 0.478584, 0.471858, 0.465173, 0.458449, 0.451954, 0.448019, 0.443305, 0.436261, 0.430589, 0.424819,
    0.420179, 0.409927, 0.406655, 0.398825, 0.391145, 0.387928, 0.380033, 0.378482, 0.372795, 0.369679, 0.362205, 0.359995, 0.351918, 0.34995, 0.348549,
    0.347907, 0.341093, 0.341015, 0.332198, 0.331281, 0.322228, 0.316669, 0.315569, 0.310077, 0.30713, 0.304674, 0.296022, 0.29109, 0.287612, 0.282751,
    0.282227, 0.277435, 0.276759, 0.271491, 0.270748, 0.263364, 0.258755, 0.258047, 0.251406, 0.250064, 0.244264, 0.243818, 0.239612, 0.239024,
    0.232805, 0.232168, 0.226194, 0.225387, 0.224028, 0.224027, 0.224011, 0.22401, 0.223994, 0.223993, 0.223979, 0.223977, 0.223962, 0.22396, 0.223947,
    0.223943, 0.22393, 0.223926, 0.223915, 0.223909, 0.223904, 0.223904, 0.223887, 0.223887, 0.226011, 0.225818, 0.224086, 0.223853, 0.22384, 0.225949,
    0.225988, 0.225971, 0.225955, 0.225954, 0.225938, 0.225921, 0.225921, 0.225904, 0.223951, 0.224158, 0.22588, 0.225878, 0.225863, 0.225861, 0.225846,
    0.225844, 0.225829, 0.225827, 0.225812, 0.22581, 0.225794, 0.225793, 0.225774, 0.225774, 0.225759, 0.225757, 0.227901, 0.227913, 0.227897, 0.227896
])
_dP_staggered_Re_15 = np.array([9.34201, 8.81965, 8.28809, 7.42806, 6.97391, 6.57517, 5.84093, 5.50985, 5.16014, 4.93488, 4.68126, 4.42254, 3.99955, 3.773,
    3.39505, 3.20519, 3.02598, 2.77577, 2.61488, 2.474, 2.33566, 2.20505, 1.96531, 1.8554, 1.76851, 1.68568, 1.60674, 1.54592, 1.47385, 1.45584,
    1.42566, 1.36641, 1.35191, 1.29626, 1.28859, 1.24598, 1.24005, 1.18197, 1.17596, 1.13745, 1.13449, 1.10514, 1.04611, 1.03299, 1.01551, 1.00639,
    0.975508, 0.956979, 0.921361, 0.906001, 0.886645, 0.876509, 0.861323, 0.848885, 0.833067, 0.820018, 0.790987, 0.781353, 0.757982, 0.750599, 0.73523,
    0.72878, 0.715526, 0.703825, 0.690704, 0.69043, 0.671089, 0.670816, 0.658238, 0.65804, 0.642607, 0.638042, 0.628642, 0.616468, 0.611099, 0.59789,
    0.592593, 0.59088, 0.5807, 0.571709, 0.569635, 0.559848, 0.558786, 0.554428, 0.553416, 0.5491, 0.548097, 0.54293, 0.542793, 0.537633, 0.53548,
    0.52734, 0.525928, 0.522325, 0.519436, 0.51244, 0.510312, 0.502563, 0.501212, 0.497646, 0.483767, 0.483639, 0.479479, 0.478991, 0.469919, 0.469457,
    0.465373, 0.464541, 0.457403, 0.456485, 0.452112, 0.44443, 0.443408, 0.435131, 0.434907, 0.419981, 0.418722, 0.415054, 0.414669, 0.405475, 0.405291,
    0.396251, 0.391403, 0.387694, 0.383945, 0.378953, 0.373041, 0.369506, 0.365933, 0.360178, 0.355541, 0.350503, 0.34544, 0.342437, 0.338861, 0.33562,
    0.326088, 0.324262, 0.319875, 0.312702, 0.30994, 0.303633, 0.301961, 0.295857, 0.293384, 0.286801, 0.285051, 0.281193, 0.27962, 0.27688, 0.276192,
    0.269144, 0.269082, 0.261395, 0.260961, 0.256484, 0.249175, 0.248418, 0.244472, 0.240616, 0.237428, 0.23135, 0.228333, 0.226286, 0.219953, 0.21934,
    0.21432, 0.213615, 0.209306, 0.208785, 0.203406, 0.198042, 0.197549, 0.193322, 0.192633, 0.189133, 0.188615, 0.183883, 0.183431, 0.178539, 0.17805,
    0.173635, 0.172752, 0.171298, 0.171157, 0.169685, 0.169823, 0.171289, 0.171462, 0.172926, 0.173289, 0.176258, 0.176871, 0.181386, 0.182469,
    0.186641, 0.188307, 0.193913, 0.196789, 0.199552, 0.199594, 0.201486, 0.2015, 0.203218, 0.203417, 0.203404, 0.203401, 0.204688, 0.205335, 0.205334,
    0.203367, 0.203354, 0.203352, 0.203338, 0.205273, 0.20528, 0.205265, 0.205258, 0.205257, 0.205243, 0.205241, 0.205227, 0.205226, 0.205212, 0.20521,
    0.205196, 0.205195, 0.205181, 0.205179, 0.205165, 0.205164, 0.205146, 0.205146, 0.205132, 0.205131, 0.205117, 0.205115, 0.205101, 0.2051
])
_dP_staggered_Re_2 = np.array([3.3699, 3.25874, 3.1513, 2.97524, 2.87715, 2.78229, 2.60185, 2.504, 2.4214, 2.36801, 2.2862, 2.21078, 2.08731, 2.01849, 1.89955,
    1.82808, 1.76778, 1.68508, 1.61934, 1.56066, 1.50918, 1.4524, 1.33872, 1.28835, 1.23986, 1.19319, 1.14827, 1.10908, 1.07889, 1.06407, 1.03929,
    1.00291, 0.994386, 0.957472, 0.951802, 0.912623, 0.908283, 0.874086, 0.869647, 0.841073, 0.838095, 0.808676, 0.780364, 0.773598, 0.747536, 0.738905,
    0.721828, 0.717582, 0.690875, 0.682216, 0.671254, 0.666188, 0.658464, 0.647496, 0.633663, 0.625691, 0.607864, 0.60192, 0.586506, 0.581184, 0.573473,
    0.57011, 0.559368, 0.551449, 0.543432, 0.543274, 0.533071, 0.532917, 0.522924, 0.522784, 0.512946, 0.509741, 0.503124, 0.493595, 0.490661, 0.483683,
    0.479474, 0.477483, 0.469851, 0.466187, 0.465338, 0.461708, 0.461273, 0.453348, 0.452088, 0.448562, 0.447435, 0.443915, 0.443836, 0.439616, 0.43882,
    0.43577, 0.434512, 0.431212, 0.430014, 0.427098, 0.426293, 0.423332, 0.422987, 0.422964, 0.422929, 0.422883, 0.414874, 0.414451, 0.410887, 0.410884,
    0.410855, 0.410436, 0.40691, 0.406003, 0.40083, 0.393272, 0.392277, 0.385608, 0.385474, 0.374217, 0.373188, 0.36608, 0.365067, 0.355721, 0.355584,
    0.349483, 0.344411, 0.338995, 0.335717, 0.333088, 0.328254, 0.323091, 0.319967, 0.316935, 0.312854, 0.307934, 0.303486, 0.299932, 0.296289,
    0.293462, 0.288427, 0.286092, 0.279681, 0.274029, 0.271776, 0.265638, 0.264031, 0.260457, 0.258987, 0.253176, 0.251647, 0.24824, 0.2468, 0.243526,
    0.242183, 0.237587, 0.237538, 0.231397, 0.230821, 0.224266, 0.218493, 0.217895, 0.215809, 0.213044, 0.210747, 0.20588, 0.202787, 0.200602, 0.196037,
    0.195433, 0.19047, 0.189774, 0.185568, 0.18506, 0.181897, 0.176863, 0.176379, 0.172288, 0.171368, 0.166958, 0.166501, 0.162215, 0.161773, 0.158952,
    0.15869, 0.15501, 0.154182, 0.153022, 0.152707, 0.151364, 0.15124, 0.152546, 0.152684, 0.155311, 0.155668, 0.158336, 0.158692, 0.162743, 0.164018,
    0.169607, 0.171511, 0.177917, 0.179674, 0.181351, 0.181379, 0.184846, 0.184874, 0.188409, 0.188408, 0.188396, 0.18876, 0.190196, 0.190315, 0.190318,
    0.190617, 0.190888, 0.190917, 0.191188, 0.191489, 0.191491, 0.191793, 0.191913, 0.191942, 0.191929, 0.191928, 0.191915, 0.191913, 0.1919, 0.192079,
    0.193733, 0.193731, 0.193718, 0.193717, 0.193703, 0.193702, 0.193686, 0.193686, 0.193673, 0.193861, 0.195522, 0.195521, 0.195508, 0.195506
])
_dP_staggered_Re_25 = np.array([1.79994, 1.76013, 1.72122, 1.65648, 1.61986, 1.58405, 1.51479, 1.47657, 1.44391, 1.4226, 1.38964, 1.3589, 1.30781, 1.2789,
    1.22814, 1.19714, 1.17066, 1.13385, 1.10416, 1.07732, 1.05349, 1.02689, 0.972573, 0.948019, 0.924073, 0.900732, 0.877981, 0.857886, 0.842238,
    0.834508, 0.821498, 0.802211, 0.797489, 0.771119, 0.767464, 0.742087, 0.738758, 0.71986, 0.717012, 0.693528, 0.691126, 0.673248, 0.655161, 0.650796,
    0.633605, 0.627855, 0.611017, 0.606947, 0.589142, 0.581418, 0.572075, 0.564906, 0.555118, 0.548858, 0.542958, 0.537932, 0.523109, 0.517617,
    0.503395, 0.500444, 0.493804, 0.488993, 0.479779, 0.472711, 0.470631, 0.4705, 0.461663, 0.461524, 0.45287, 0.452758, 0.444238, 0.442841, 0.439921,
    0.431589, 0.431576, 0.423352, 0.4167, 0.415283, 0.415257, 0.412759, 0.412007, 0.408794, 0.408443, 0.405032, 0.404211, 0.400713, 0.399901, 0.39662,
    0.396488, 0.389473, 0.388156, 0.385458, 0.384426, 0.381792, 0.380731, 0.377866, 0.377075, 0.377054, 0.377046, 0.374429, 0.36984, 0.369804, 0.366623,
    0.366285, 0.36626, 0.366258, 0.363072, 0.362738, 0.359622, 0.35915, 0.352384, 0.349036, 0.348637, 0.345681, 0.345518, 0.336581, 0.335833, 0.330069,
    0.329459, 0.320103, 0.320041, 0.316923, 0.313944, 0.310956, 0.305966, 0.302055, 0.299216, 0.296371, 0.292087, 0.287957, 0.285478, 0.282464,
    0.277935, 0.274359, 0.271138, 0.268545, 0.263228, 0.261591, 0.256305, 0.250791, 0.248501, 0.244499, 0.2436, 0.239026, 0.236807, 0.231877, 0.230603,
    0.225941, 0.22405, 0.222707, 0.222159, 0.217943, 0.217893, 0.21226, 0.211731, 0.206127, 0.20064, 0.200073, 0.197111, 0.194215, 0.192662, 0.188591,
    0.185104, 0.182162, 0.178493, 0.178125, 0.174048, 0.173476, 0.170156, 0.169754, 0.16495, 0.160643, 0.160246, 0.156122, 0.155402, 0.152988, 0.15273,
    0.148798, 0.148394, 0.144533, 0.144169, 0.139245, 0.138483, 0.137648, 0.137427, 0.136218, 0.136117, 0.137425, 0.137564, 0.138759, 0.139196,
    0.142785, 0.143115, 0.145559, 0.14672, 0.151214, 0.152571, 0.157129, 0.160246, 0.163232, 0.163273, 0.168458, 0.168493, 0.172862, 0.173428, 0.177879,
    0.178569, 0.181323, 0.18658, 0.18658, 0.186566, 0.186553, 0.186552, 0.186539, 0.186525, 0.186508, 0.184125, 0.183189, 0.182964, 0.182952, 0.18295,
    0.182938, 0.182936, 0.182924, 0.182922, 0.18291, 0.182909, 0.184483, 0.184655, 0.184643, 0.184641, 0.182866, 0.182873, 0.18444, 0.184612, 0.184599,
    0.184598, 0.184585, 0.184584
])
_dP_staggered_Re_parameters = np.array([_dP_staggered_Re_125, _dP_staggered_Re_15, _dP_staggered_Re_2, _dP_staggered_Re_25]).T
dP_staggered_f = RectBivariateSpline(_dP_staggered_Res, np.array([1.25, 1.5, 2, 2.5]), _dP_staggered_Re_parameters, kx=3, ky=3, s=0.002)


_dP_staggered_correction_parameters = np.array([0.4387, 0.470647, 0.494366, 0.52085, 0.542787, 0.583019, 0.609319, 0.659047, 0.685413, 0.729582, 0.800982,
    0.84214, 0.892449, 0.947309, 1.00903, 1.07052, 1.16389, 1.22243, 1.26584, 1.32314, 1.37597, 1.40437, 1.45385, 1.51093, 1.55814, 1.61775, 1.68647,
    1.74589, 1.79853, 1.86586, 1.92335, 1.97322, 2.12053, 2.22751, 2.34521, 2.45793, 2.58193, 2.71226, 2.84909, 2.99282, 3.14389, 3.22668, 3.32915,
    3.54351
])
_dP_staggered_correction_Re_100 = np.array([0.996741, 0.996986, 0.997157, 0.997339, 0.997482, 0.997731, 0.997885, 0.998158, 0.998294, 0.998512, 0.998836,
    0.999011, 0.999213, 0.99942, 0.99964, 0.999846, 1.00241, 1.02216, 1.0392, 1.06545, 1.08705, 1.0995, 1.1206, 1.14708, 1.16583, 1.18871, 1.21407,
    1.23518, 1.25628, 1.27868, 1.29996, 1.31593, 1.36025, 1.39055, 1.42224, 1.45114, 1.48144, 1.51175, 1.54205, 1.57235, 1.60267, 1.62032, 1.64208,
    1.68552
])
_dP_staggered_correction_Re_1000 = np.array([1.03576, 1.02714, 1.02111, 1.01712, 1.01206, 1.00798, 1.00547, 1.001, 0.999839, 0.999378, 0.998689, 0.998319,
    0.997891, 0.997451, 0.996985, 0.999249, 1.00245, 1.0135, 1.02415, 1.03618, 1.04682, 1.0534, 1.06478, 1.07524, 1.0836, 1.09539, 1.10811, 1.11825,
    1.12833, 1.13858, 1.1481, 1.15678, 1.17941, 1.19487, 1.21106, 1.22398, 1.24068, 1.25657, 1.27109, 1.28706, 1.30317, 1.31111, 1.3196, 1.33956
])
_dP_staggered_correction_Re_10000 = np.array([1.20211, 1.18293, 1.16951, 1.15527, 1.14308, 1.12148, 1.10821, 1.09069, 1.08213, 1.06633, 1.04824, 1.04041,
    1.03015, 1.02269, 1.01509, 1.00905, 1.00302, 1.00302, 1.00304, 1.00623, 1.00905, 1.0103, 1.01246, 1.01508, 1.01696, 1.01926, 1.0225, 1.02674,
    1.03074, 1.03432, 1.03618, 1.03931, 1.04813, 1.05451, 1.05855, 1.0674, 1.07355, 1.08006, 1.08719, 1.09572, 1.10324, 1.10854, 1.11428, 1.12663
])
_dP_staggered_correction_Re_100000 = np.array([1.45829, 1.42587, 1.40486, 1.38291, 1.36389, 1.32864, 1.30754, 1.27136, 1.25327, 1.22447, 1.18203, 1.15678,
    1.12845, 1.10251, 1.07182, 1.04763, 1.00824, 0.984925, 0.975402, 0.965711, 0.960152, 0.957646, 0.9534, 0.948334, 0.945015, 0.942714, 0.940164,
    0.937857, 0.936683, 0.936683, 0.934823, 0.933668, 0.933668, 0.933668, 0.933668, 0.933668, 0.933668, 0.936683, 0.936683, 0.936683, 0.939698,
    0.939698, 0.939698, 0.939698
])
_dP_staggered_correction_Re_parameters = np.array([_dP_staggered_correction_Re_100, _dP_staggered_correction_Re_1000, _dP_staggered_correction_Re_10000, _dP_staggered_correction_Re_100000]).T
dP_staggered_correction = RectBivariateSpline(_dP_staggered_correction_parameters, np.array([1E2, 1E3, 1E4, 1E5]), _dP_staggered_correction_Re_parameters, kx=1, ky=3, s=0.002)


_dP_inline_Res = np.array([28.5094, 30.8092, 32.9727, 35.3563, 41.2101, 45.9365, 49.1622, 52.6143, 56.3102, 59.107, 63.7533, 68.3605, 73.1607, 82.9896, 91.2679,
    107.829, 116.528, 124.713, 134.774, 144.237, 157.106, 169.784, 183.484, 202.173, 218.488, 241.163, 278.938, 301.447, 325.772, 352.069, 402.667,
    439.431, 479.551, 528.457, 576.706, 600.39, 654.321, 666.665, 722.026, 795.679, 802.401, 883.594, 965.211, 973.774, 1022.26, 1107.38, 1126.59,
    1220.48, 1343.51, 1368.32, 1468.16, 1616.19, 1646.72, 1764.04, 1814.79, 1944.21, 1998.93, 2038.12, 2041.06, 2246.18, 2249.48, 2455.2, 2476.81,
    2705.84, 2729.59, 2982.07, 3008.17, 3257.9, 3313.34, 3590.4, 3618.29, 3946.71, 4030.55, 4063.47, 4434.98, 4446.05, 4852.32, 4895.14, 5347.3,
    5394.74, 5830.48, 5994.16, 6003.24, 6545.85, 6615.94, 7143.99, 7226.2, 7873.1, 8101.49, 8113.39, 8928.33, 8941.23, 9765.31, 9845.06, 10343.9,
    10430.3, 11407.3, 11956.6, 12562.5, 13176.9, 13719.7, 14521.4, 15236.6, 16651, 17465.4, 18505, 20393.2, 20419.3, 22474.5, 22503.3, 24559, 25546.2,
    27064.9, 29789.7, 30724.6, 32829.2, 34810.9, 36179.8, 38362.8, 39871.4, 40721.2, 41061.4, 44854.2, 45239.5, 48975.7, 49855.5, 53971.7, 54426.4,
    59979.7, 60058.1, 66101.3, 66184.5, 72230.6, 72907, 81043.8, 81128.8, 89317.2, 89406.8, 97574.2, 98430.6, 103433, 104341, 112924, 114990, 123239,
    126726, 135811, 139659, 149668, 153913, 163348, 169621, 180015, 186933, 206011, 206189, 227042, 227233, 247788, 250418, 273078, 275976, 300948,
    304142, 331663, 335183, 365513, 369392, 406751, 407092, 448264, 448640, 494013, 494428, 544433, 544890, 605857, 606365, 667691, 668251, 735835,
    736453, 803766, 810935, 877478, 893699, 967033, 984910, 1044050, 1044920, 1150600, 1151570, 1268030, 1269100, 1397450, 1398620, 1540070, 1541370,
    1697250, 1698680, 1854500, 1871040
])
_dP_inline_Re_125 = np.array([5.93109, 5.54354, 5.22463, 4.91025, 4.2207, 3.80075, 3.54753, 3.31117, 3.12106, 2.97108, 2.75394, 2.58829, 2.41584, 2.14646,
    1.9677, 1.6944, 1.58146, 1.49066, 1.3913, 1.29861, 1.20507, 1.12508, 1.05285, 0.971815, 0.909568, 0.833438, 0.747763, 0.704808, 0.66432, 0.632336,
    0.581074, 0.549915, 0.52122, 0.493379, 0.470594, 0.461052, 0.443442, 0.440821, 0.430173, 0.421676, 0.421664, 0.422183, 0.429662, 0.431075, 0.438954,
    0.446788, 0.449097, 0.46, 0.468865, 0.471657, 0.482859, 0.492167, 0.493224, 0.496938, 0.499697, 0.506586, 0.50325, 0.502485, 0.502646, 0.512335,
    0.512408, 0.516812, 0.517255, 0.52129, 0.521276, 0.521127, 0.521113, 0.520979, 0.520951, 0.520816, 0.520351, 0.51557, 0.515536, 0.515148, 0.51047,
    0.510337, 0.505209, 0.504298, 0.49523, 0.493744, 0.480865, 0.480679, 0.480676, 0.476399, 0.47587, 0.467664, 0.466446, 0.453034, 0.456863, 0.457087,
    0.448375, 0.448242, 0.439335, 0.438121, 0.430813, 0.430369, 0.426369, 0.421825, 0.417567, 0.415493, 0.413748, 0.40895, 0.404931, 0.397616, 0.393735,
    0.389087, 0.3814, 0.3813, 0.373863, 0.373765, 0.366718, 0.36344, 0.361258, 0.355173, 0.352681, 0.347915, 0.343752, 0.341039, 0.33675, 0.333804,
    0.332203, 0.331636, 0.325673, 0.325338, 0.322369, 0.321193, 0.316002, 0.315506, 0.309826, 0.30975, 0.303711, 0.303632, 0.297644, 0.297168, 0.291819,
    0.291767, 0.288848, 0.288818, 0.283136, 0.281514, 0.272212, 0.272406, 0.274764, 0.273631, 0.269345, 0.267807, 0.264025, 0.263257, 0.261364, 0.26134,
    0.26129, 0.260266, 0.258656, 0.257969, 0.256205, 0.25619, 0.255938, 0.255937, 0.253893, 0.253614, 0.253287, 0.253278, 0.253208, 0.253199, 0.251176,
    0.2509, 0.250577, 0.250568, 0.250491, 0.25049, 0.250412, 0.250412, 0.250334, 0.250333, 0.250256, 0.250255, 0.25017, 0.250169, 0.250092, 0.250091,
    0.250013, 0.250013, 0.249942, 0.250177, 0.252337, 0.252322, 0.252258, 0.252244, 0.252196, 0.252196, 0.252117, 0.252117, 0.252039, 0.252038, 0.25196,
    0.251959, 0.251881, 0.25188, 0.251802, 0.251802, 0.254214, 0.25446
])
_dP_inline_Re_15 = np.array([2.51237, 2.49499, 2.32876, 2.1908, 1.87501, 1.68786, 1.5828, 1.484, 1.38705, 1.31326, 1.23965, 1.16623, 1.08879, 0.973353, 0.88678,
    0.773105, 0.72388, 0.681815, 0.636838, 0.600558, 0.55801, 0.525955, 0.495741, 0.458149, 0.43183, 0.403164, 0.367208, 0.350209, 0.334532, 0.32017,
    0.299699, 0.288076, 0.276903, 0.268782, 0.258357, 0.25326, 0.250756, 0.249796, 0.245772, 0.243513, 0.243318, 0.245622, 0.252914, 0.25366, 0.257801,
    0.264766, 0.266548, 0.276173, 0.284237, 0.286562, 0.295607, 0.301306, 0.303191, 0.310225, 0.312873, 0.319399, 0.321166, 0.322408, 0.3225, 0.328697,
    0.328793, 0.335219, 0.335506, 0.338421, 0.33871, 0.341653, 0.341978, 0.344926, 0.344907, 0.344818, 0.344809, 0.344713, 0.34469, 0.344681, 0.344584,
    0.344549, 0.341421, 0.341109, 0.341012, 0.341002, 0.331021, 0.337212, 0.337554, 0.33746, 0.337449, 0.334469, 0.334034, 0.33154, 0.330712, 0.33067,
    0.327386, 0.327336, 0.324341, 0.324066, 0.320821, 0.320812, 0.320676, 0.317593, 0.314385, 0.312656, 0.311204, 0.309367, 0.30782, 0.304983, 0.303469,
    0.301435, 0.296008, 0.295937, 0.295845, 0.295844, 0.29001, 0.28882, 0.287086, 0.284229, 0.28322, 0.280847, 0.277486, 0.275535, 0.273856, 0.272992,
    0.272948, 0.272482, 0.267582, 0.267318, 0.264881, 0.264389, 0.262202, 0.261791, 0.257077, 0.257024, 0.254467, 0.254434, 0.252125, 0.25188, 0.246946,
    0.246897, 0.244434, 0.244409, 0.239588, 0.239582, 0.239543, 0.239114, 0.235263, 0.234574, 0.232704, 0.232439, 0.232387, 0.231931, 0.230263,
    0.230024, 0.22998, 0.229521, 0.228102, 0.227634, 0.227563, 0.227562, 0.227491, 0.227491, 0.225446, 0.225198, 0.225135, 0.225127, 0.225065, 0.225057,
    0.224994, 0.224987, 0.224924, 0.224916, 0.224846, 0.224846, 0.224776, 0.224776, 0.224706, 0.224705, 0.224636, 0.224635, 0.224558, 0.224558,
    0.224488, 0.224488, 0.224418, 0.224417, 0.224354, 0.224348, 0.224291, 0.224278, 0.224221, 0.224208, 0.224166, 0.224165, 0.224095, 0.224095,
    0.224025, 0.224025, 0.223955, 0.223955, 0.223885, 0.223885, 0.223815, 0.223815, 0.223752, 0.223745
])
_dP_inline_Re_2 = np.array([0.225144, 0.225088, 0.225039, 0.224988, 0.224877, 0.224799, 0.22475, 0.224701, 0.224652, 0.224617, 0.224562, 0.224511, 0.224462,
    0.224371, 0.224303, 0.224182, 0.224127, 0.224078, 0.224022, 0.223973, 0.223911, 0.223855, 0.223799, 0.22373, 0.223674, 0.223603, 0.223498, 0.223442,
    0.223386, 0.223331, 0.223234, 0.223171, 0.223109, 0.223039, 0.222976, 0.222947, 0.222886, 0.222872, 0.222815, 0.222745, 0.222739, 0.22267, 0.222607,
    0.222601, 0.222566, 0.222509, 0.222496, 0.222439, 0.22237, 0.222357, 0.222307, 0.222238, 0.222225, 0.222176, 0.222155, 0.222106, 0.222086, 0.222072,
    0.222091, 0.224181, 0.224192, 0.224129, 0.224123, 0.224059, 0.224053, 0.223989, 0.223983, 0.225938, 0.226122, 0.226064, 0.226058, 0.225995, 0.22598,
    0.225974, 0.22591, 0.225909, 0.225845, 0.225839, 0.225774, 0.225768, 0.225712, 0.225692, 0.225715, 0.227854, 0.227574, 0.225564, 0.225556, 0.225494,
    0.225473, 0.225472, 0.225402, 0.225401, 0.225337, 0.225331, 0.224173, 0.223979, 0.221897, 0.220812, 0.220777, 0.220743, 0.219816, 0.218518,
    0.217425, 0.215326, 0.214141, 0.212854, 0.209889, 0.209854, 0.207766, 0.207721, 0.204025, 0.20238, 0.199994, 0.196092, 0.194852, 0.192218, 0.189918,
    0.189156, 0.188004, 0.185898, 0.184756, 0.184308, 0.182455, 0.18245, 0.182403, 0.182219, 0.180718, 0.18056, 0.17874, 0.178739, 0.178684, 0.178683,
    0.178633, 0.178614, 0.176826, 0.176836, 0.178506, 0.17851, 0.17846, 0.178455, 0.178427, 0.178422, 0.178376, 0.178366, 0.178326, 0.17831, 0.17827,
    0.178254, 0.178215, 0.178199, 0.179233, 0.179895, 0.179866, 0.179844, 0.179788, 0.179788, 0.179732, 0.179731, 0.179681, 0.179675, 0.179625,
    0.179619, 0.179569, 0.179563, 0.179513, 0.179507, 0.179457, 0.179451, 0.179395, 0.179395, 0.179339, 0.179339, 0.179283, 0.179282, 0.179227,
    0.179226, 0.179165, 0.179165, 0.179109, 0.179109, 0.179053, 0.179053, 0.179002, 0.178997, 0.178952, 0.178941, 0.178896, 0.178885, 0.178852,
    0.178851, 0.178796, 0.178795, 0.17874, 0.178739, 0.178684, 0.178684, 0.178628, 0.178628, 0.178572, 0.178572, 0.178521, 0.178516
])
_dP_inline_Re_25 = np.array([0.349884, 0.344353, 0.339587, 0.334753, 0.324384, 0.31723, 0.31284, 0.308509, 0.304238, 0.301224, 0.296579, 0.292359, 0.288312,
    0.280944, 0.275511, 0.266235, 0.262027, 0.258398, 0.254314, 0.250794, 0.24643, 0.242534, 0.238699, 0.233991, 0.230291, 0.225667, 0.219023, 0.21556,
    0.212151, 0.208795, 0.203116, 0.199504, 0.195956, 0.192086, 0.18867, 0.187117, 0.18384, 0.183136, 0.179837, 0.176255, 0.175964, 0.174204, 0.174155,
    0.17415, 0.174122, 0.174078, 0.174068, 0.175436, 0.175686, 0.175676, 0.175636, 0.175582, 0.175571, 0.175532, 0.175516, 0.176657, 0.177193, 0.175451,
    0.175475, 0.177126, 0.177125, 0.177076, 0.177071, 0.17702, 0.177015, 0.176965, 0.17696, 0.176915, 0.176905, 0.176859, 0.176855, 0.176805, 0.176793,
    0.176789, 0.178483, 0.178481, 0.178431, 0.178426, 0.178375, 0.17837, 0.178326, 0.17831, 0.178309, 0.178259, 0.178253, 0.178209, 0.178203, 0.178154,
    0.178137, 0.178136, 0.178082, 0.178081, 0.17803, 0.178026, 0.177997, 0.177992, 0.177941, 0.177208, 0.176296, 0.175343, 0.174528, 0.175213, 0.176039,
    0.175988, 0.175263, 0.17421, 0.172454, 0.172453, 0.1724, 0.172399, 0.17235, 0.171731, 0.170592, 0.168894, 0.168351, 0.167192, 0.16716, 0.167139,
    0.166121, 0.165455, 0.165443, 0.165435, 0.163918, 0.163771, 0.162422, 0.162121, 0.160642, 0.1605, 0.16361, 0.163528, 0.158824, 0.158823, 0.158779,
    0.158774, 0.15872, 0.158736, 0.160236, 0.160219, 0.158765, 0.15862, 0.158595, 0.158591, 0.15855, 0.158541, 0.158506, 0.158492, 0.158456, 0.158442,
    0.158407, 0.158392, 0.158362, 0.158343, 0.158313, 0.158293, 0.158244, 0.158257, 0.159755, 0.15974, 0.15815, 0.158145, 0.158101, 0.158095, 0.158051,
    0.158046, 0.158002, 0.157996, 0.157952, 0.157947, 0.157898, 0.157898, 0.157849, 0.157848, 0.157799, 0.157799, 0.15775, 0.15775, 0.157696, 0.157695,
    0.157646, 0.157646, 0.157597, 0.157597, 0.157552, 0.157548, 0.157508, 0.157499, 0.157459, 0.157449, 0.15742, 0.157419, 0.157371, 0.15737, 0.157321,
    0.157321, 0.157272, 0.157272, 0.157223, 0.157223, 0.157174, 0.157173, 0.157129, 0.157125
])
_dP_inline_Re_parameters = np.array([_dP_inline_Re_125, _dP_inline_Re_15, _dP_inline_Re_2, _dP_inline_Re_25]).T
dP_inline_f = RectBivariateSpline(_dP_inline_Res, np.array([1.25, 1.5, 2, 2.5]), _dP_inline_Re_parameters, kx = 3, ky = 3, s = 0.002)


_dP_inline_correction_parameters = np.array([0.0661637, 0.0767956, 0.0811521, 0.091014, 0.0965946, 0.102863, 0.114663, 0.117455, 0.132109, 0.135196, 0.152089,
    0.168558, 0.19133, 0.192037, 0.21534, 0.217736, 0.244667, 0.247747, 0.324839, 0.392087, 0.446129, 2.2286, 2.3885, 2.63783, 2.92864, 3.00382,
    4.05259, 4.2551, 4.54434, 4.84314, 5.09577, 5.59171, 5.71411
])
_dP_inline_correction_Re_1000 = np.array([7.53832, 6.86113, 6.54006, 6.09616, 5.93568, 5.34629, 5.0612, 4.9696, 4.55428, 4.48266, 4.13474, 3.85306, 3.53216,
    3.52323, 3.22988, 3.19898, 2.89667, 2.86799, 2.31194, 1.99054, 1.798, 0.557156, 0.529536, 0.491093, 0.453615, 0.444813, 0.351914, 0.339127,
    0.322613, 0.30739, 0.295752, 0.27562, 0.271127
])
_dP_inline_correction_Re_10000 = np.array([6.19059, 5.63447, 5.44146, 5.0612, 4.86597, 4.66786, 4.34453, 4.27598, 3.95623, 3.88747, 3.57369, 3.37337, 3.09718,
    3.08911, 2.83271, 2.81518, 2.63689, 2.61495, 2.18225, 1.92462, 1.76564, 0.603218, 0.575945, 0.534133, 0.499018, 0.491093, 0.401321, 0.388344,
    0.370649, 0.353159, 0.339788, 0.316659, 0.311496
])
_dP_inline_correction_Re_100000 = np.array([4.50727, 4.13004, 3.99851, 3.73838, 3.61014, 3.47942, 3.31256, 3.27702, 3.10877, 3.0728, 2.87638, 2.71515, 2.52473,
    2.52055, 2.39441, 2.38256, 2.23167, 2.21606, 1.89994, 1.70733, 1.58802, 0.668818, 0.644362, 0.610869, 0.577472, 0.569658, 0.484948, 0.4719,
    0.454805, 0.438843, 0.426501, 0.404846, 0.399958
])
_dP_inline_correction_Re_1000000 = np.array([3.14214, 2.9391, 2.8673, 2.72361, 2.64416, 2.56157, 2.46985, 2.45024, 2.36473, 2.34829, 2.22756, 2.1327, 2.02212,
    2.01899, 1.92414, 1.91509, 1.81755, 1.80738, 1.63471, 1.50647, 1.43004, 0.74756, 0.730366, 0.704554, 0.675458, 0.668194, 0.588052, 0.575945,
    0.563366, 0.551447, 0.540255, 0.520396, 0.515871
])
_dP_inline_correction_Re_parameters = np.array([_dP_inline_correction_Re_1000, _dP_inline_correction_Re_10000, _dP_inline_correction_Re_100000, _dP_inline_correction_Re_1000000]).T
dP_inline_correction = RectBivariateSpline(_dP_inline_correction_parameters, np.array([1E3, 1E4, 1E5, 1E6]), _dP_inline_correction_Re_parameters, kx=1, ky=3, s=0.002)


def dP_Zukauskas(Re, n, ST, SL, D, rho, Vmax):
    r'''Calculates pressure drop for crossflow across a tube bank
    of tube number n at a specified Re. Method presented in [1]_.
    Also presented in [2]_.

    .. math::
        \Delta P = N_L \chi \left(\frac{\rho V_{max}^2}{2}\right)f

    Parameters
    ----------
    Re : float
        Reynolds number, [-]
    n : float
        Number of tube rows, [-]
    ST : float
        Transverse pitch, used only by some conditions, [m]
    SL : float
        Longitudal pitch, used only by some conditions, [m]
    D : float
        Tube outer diameter, [m]
    rho : float
        Fluid density, [kg/m^3]
    Vmax : float
        Maximum velocity, [m/s]

    Returns
    -------
    dP : float
        Pressure drop, [Pa]

    Notes
    -----
    Does not account for effects in a heat exchanger.
    Example 2 is from [2]_. Matches to 0.3%; figures are very approximate.
    Interpolation used with 4 graphs to obtain friction factor and a
    correction factor.

    Examples
    --------
    >>> dP_Zukauskas(Re=13943., n=7, ST=0.0313, SL=0.0343, D=0.0164, rho=1.217, Vmax=12.6)
    235.22916169118335
    >>> dP_Zukauskas(Re=13943., n=7, ST=0.0313, SL=0.0313, D=0.0164, rho=1.217, Vmax=12.6)
    217.0750033117563

    References
    ----------
    .. [1] Zukauskas, A. Heat transfer from tubes in crossflow. In T.F. Irvine,
       Jr. and J. P. Hartnett, editors, Advances in Heat Transfer, volume 8,
       pages 93-160. Academic Press, Inc., New York, 1972.
    .. [2] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    a = ST/D
    b = SL/D
    if a == b:
        parameter = (a-1.)/(b-1.)
        f = float(dP_inline_f(Re, b))
        x = float(dP_inline_correction(parameter, Re))
    else:
        parameter = a/b
        f = float(dP_staggered_f(Re, a))
        x = float(dP_staggered_correction(parameter, Re))

    return n*x*f*rho/2*Vmax**2

Bell_baffle_configuration_Fcs = np.array([0, 0.0138889, 0.0277778, 0.0416667, 0.0538194, 0.0659722, 0.100694, 0.114583,
    0.126736, 0.140625, 0.152778, 0.166667, 0.178819, 0.192708, 0.215278, 0.227431, 0.241319, 0.255208,
    0.267361, 0.28125, 0.295139, 0.340278, 0.354167, 0.366319, 0.380208, 0.394097, 0.402778, 0.416667, 0.430556,
    0.444444, 0.475694, 0.489583, 0.503472, 0.517361, 0.53125, 0.545139, 0.560764, 0.574653, 0.588542, 0.625,
    0.638889, 0.652778, 0.668403, 0.682292, 0.697917, 0.701389, 0.713542, 0.729167, 0.743056, 0.758681,
    0.802083, 0.817708, 0.833333, 0.848958, 0.866319, 0.881944, 0.901042, 0.918403, 0.934028, 0.947917,
    0.960069, 0.970486, 0.977431, 0.984375, 0.991319, 0.994792, 1
])
Bell_baffle_configuration_Jcs = np.array([0.534317, 0.544632, 0.556665, 0.566983, 0.579014, 0.591045, 0.620271,
    0.630589, 0.640904, 0.652937, 0.663252, 0.675286, 0.685601, 0.697635, 0.71483, 0.725145, 0.737179, 0.747497,
    0.757812, 0.76813, 0.780163, 0.81627, 0.826588, 0.836903, 0.847221, 0.857539, 0.867848, 0.874734, 0.885052,
    0.89537, 0.916012, 0.92633, 0.936648, 0.946966, 0.955568, 0.965886, 0.974492, 0.984809, 0.993412, 1.01578,
    1.0261, 1.0347, 1.0433, 1.05362, 1.06223, 1.06052, 1.07083, 1.07944, 1.08804, 1.09664, 1.11731, 1.1242,
    1.13109, 1.13798, 1.14487, 1.15004, 1.15522, 1.15354, 1.1467, 1.13815, 1.12787, 1.11588, 1.10388, 1.09017,
    1.07474, 1.05759, 1.03015
])

'''Note: the smoothing factor was tunned to keep only 7 knots/9 coeffs while  
getting near to requiring more knots. The fitting for a digitized graph is
likely to be at the maximum possible accuracy. Any speed increasing fit 
function should fit the smoothed function, not the raw data.
'''
Bell_baffle_configuration_obj = UnivariateSpline(Bell_baffle_configuration_Fcs, 
                                                 Bell_baffle_configuration_Jcs, 
                                                 s=8e-5)
#import matplotlib.pyplot as plt
#plt.plot(Bell_baffle_configuration_Fcs, Bell_baffle_configuration_Jcs)
#pts = np.linspace(0, 1, 5000)
#plt.plot(pts, [Bell_baffle_configuration_obj(i) for i in pts])
#plt.show()

def baffle_correction_Bell(crossflow_tube_fraction):
    r'''Calculate the baffle correction factor `Jc` which accounts for
    the fact that all tubes are not in crossflow to the fluid - some
    have fluid flowing parallel to them because they are situated in 
    the "window", where the baffle is cut, instead of between the tips
    of adjacent baffles.
    
    Equal to 1 for no tubes in the window, increases to 1.15 when the
    windows are small and velocity there is high; decreases to about 0.52
    for very large baffle cuts. Well designed exchangers should typically
    have a value near 1.0.
    
    Parameters
    ----------
    crossflow_tube_fraction : float
        Fraction of tubes which are between baffle tips and not
        in the window, [-]

    Returns
    -------
    Jc : float
        Baffle correction factor in the Bell-Delaware method, [-]

    Notes
    -----
    max: ~1.1536 at ~0.9066
    min: ~0.5328 at 0
    value at 1: ~1.0314
    
    Takes ~13 us per call, and 40 us to construct the spline.
    
    This method returns NumPy arrays if given vector inputs.
    
    Examples
    --------
    For a HX with four groups of tube bundles; the top and bottom being 9 
    tubes each, in the window, and the two middle bundles having 41 tubes
    each, for a total of 100 tubes, the fraction between baffle tubes and
    not in the window is 0.82. The correction factor is then:
    
    >>> baffle_correction_Bell(0.82)
    1.1258554691854046
    
    References
    ----------
    .. [1] Bell, Kenneth J. Final Report of the Cooperative Research Program on
       Shell and Tube Heat Exchangers. University of Delaware, Engineering
       Experimental Station, 1963.
    .. [2] Bell, Kenneth J. Delaware Method for Shell-Side Design. In Heat  
       Transfer Equipment Design, by Shah, R.  K., Eleswarapu Chinna Subbarao,
       and R. A. Mashelkar. CRC Press, 1988.
    .. [3] Green, Don, and Robert Perry. Perry's Chemical Engineers' Handbook,
       Eighth Edition. McGraw-Hill Professional, 2007.
    '''
    Jc = Bell_baffle_configuration_obj(crossflow_tube_fraction)
    if Jc.shape:
        return Jc
    return float(Jc)


Bell_baffle_leakage_x = np.array([0.0, 1e-5, 1e-4, 1e-3, 0.0037779, 0.00885994, 0.012644, 0.0189629, 0.0213694, 0.0241428, 0.0289313, 0.0339093, 0.0376628,
    0.0425124, 0.0487152, 0.0523402, 0.0552542, 0.0614631, 0.0676658, 0.0719956, 0.0770838, 0.081302, 0.0885214, 0.0956308, 0.101638, 0.102145,
    0.111508, 0.119266, 0.12261, 0.129155, 0.136778, 0.144818, 0.148914, 0.15592, 0.164774, 0.16868, 0.177552, 0.181501, 0.189224, 0.196087, 0.200557,
    0.209209, 0.220317, 0.230683, 0.236096, 0.242525, 0.247198, 0.255653, 0.2591, 0.266228, 0.274193, 0.281732, 0.285993, 0.295601, 0.302042, 0.311269,
    0.312575, 0.322107, 0.33016, 0.332909, 0.341261, 0.347109, 0.353899, 0.360408, 0.369312, 0.374301, 0.380413, 0.388831, 0.392836, 0.401746, 0.403961,
    0.413723, 0.422502, 0.424825, 0.432931, 0.442274, 0.450602, 0.454815, 0.463804, 0.46923, 0.475645, 0.483563, 0.491432, 0.501277, 0.501713, 0.510247,
    0.513193, 0.523506, 0.530019, 0.534607, 0.544912, 0.550679, 0.557212, 0.563826, 0.569142, 0.576997, 0.583585, 0.588979, 0.595518, 0.601215,
    0.601702, 0.611585, 0.613221, 0.623417, 0.629753, 0.634211, 0.640009, 0.646851, 0.653971, 0.665084, 0.672758, 0.683136, 0.689056, 0.698932,
    0.702129, 0.711523, 0.712532, 0.722415, 0.724566, 0.732996, 0.738886, 0.743614
])

Bell_baffle_leakage_z_0 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.982615, 0.962505, 0.952607, 0.939987, 0.935206, 0.930216, 0.922288, 0.91564, 0.910813,
    0.904659, 0.896788, 0.892188, 0.889224, 0.883885, 0.879147, 0.875888, 0.872059, 0.868884, 0.86345, 0.858585, 0.854816, 0.854561, 0.849863, 0.846402,
    0.844911, 0.841261, 0.837352, 0.833765, 0.831938, 0.828814, 0.824864, 0.823122, 0.819164, 0.817403, 0.813958, 0.810877, 0.80887, 0.804985, 0.799998,
    0.795344, 0.792913, 0.790046, 0.787961, 0.78419, 0.782652, 0.779473, 0.776134, 0.773108, 0.771208, 0.766569, 0.762947, 0.758832, 0.758249, 0.753997,
    0.750695, 0.749592, 0.746005, 0.743396, 0.740368, 0.737464, 0.733493, 0.731267, 0.728541, 0.723847, 0.721761, 0.717786, 0.716798, 0.712444,
    0.708528, 0.707492, 0.703876, 0.699709, 0.695994, 0.694115, 0.690105, 0.687685, 0.684824, 0.681292, 0.677782, 0.672841, 0.672691, 0.669838,
    0.668675, 0.662925, 0.66002, 0.657973, 0.653377, 0.651026, 0.648404, 0.645491, 0.64312, 0.639616, 0.636677, 0.634271, 0.633926, 0.628263, 0.628045,
    0.623637, 0.622907, 0.618359, 0.615533, 0.613545, 0.611204, 0.608458, 0.605055, 0.599743, 0.596076, 0.591447, 0.588806, 0.584179, 0.582574,
    0.578371, 0.577921, 0.573513, 0.572554, 0.568793, 0.566166, 0.564057
])
Bell_baffle_leakage_z_0_25 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.969362, 0.950324, 0.942087, 0.92833, 0.923091, 0.917463, 0.908263, 0.8987, 0.89149,
    0.884407, 0.874926, 0.868404, 0.865482, 0.859179, 0.851926, 0.847458, 0.842356, 0.838126, 0.831234, 0.824993, 0.820171, 0.819781, 0.812734,
    0.807844, 0.805761, 0.801747, 0.797071, 0.792124, 0.789555, 0.785317, 0.78038, 0.778202, 0.773138, 0.77066, 0.766058, 0.76223, 0.761802, 0.754362,
    0.748168, 0.742388, 0.73989, 0.737023, 0.734092, 0.729014, 0.727092, 0.723117, 0.718675, 0.713975, 0.711407, 0.706049, 0.702306, 0.696944, 0.696185,
    0.690717, 0.686227, 0.685001, 0.681275, 0.677607, 0.67354, 0.66991, 0.664945, 0.662097, 0.658262, 0.653372, 0.651139, 0.645344, 0.644356, 0.639733,
    0.633126, 0.63202, 0.628405, 0.623295, 0.618256, 0.615613, 0.610601, 0.607588, 0.604035, 0.59965, 0.595292, 0.58984, 0.589599, 0.58484, 0.583239,
    0.578639, 0.573864, 0.570568, 0.564821, 0.562249, 0.559118, 0.554969, 0.55186, 0.54748, 0.543806, 0.540727, 0.536551, 0.532912, 0.532604, 0.528196,
    0.527417, 0.521732, 0.51779, 0.515024, 0.511791, 0.507996, 0.504098, 0.498013, 0.493805, 0.488017, 0.484304, 0.479275, 0.477805, 0.471912, 0.47135,
    0.465839, 0.464639, 0.459938, 0.456295, 0.453329
])
Bell_baffle_leakage_z_0_5 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.963548, 0.945291, 0.931697, 0.915513, 0.90935, 0.903126, 0.892379, 0.882357, 0.875546,
    0.864662, 0.854734, 0.849292, 0.844917, 0.836477, 0.828194, 0.822412, 0.815618, 0.810932, 0.803692, 0.796563, 0.790539, 0.79003, 0.780769, 0.774098,
    0.771163, 0.765418, 0.759681, 0.754353, 0.751784, 0.746512, 0.739848, 0.736908, 0.73023, 0.727831, 0.723525, 0.722361, 0.716403, 0.709498, 0.702106,
    0.695343, 0.69183, 0.687797, 0.684784, 0.679126, 0.676934, 0.672463, 0.666468, 0.660794, 0.657587, 0.652229, 0.647674, 0.641886, 0.641039, 0.634661,
    0.629571, 0.627846, 0.62156, 0.618, 0.614214, 0.609549, 0.603166, 0.599589, 0.595259, 0.589978, 0.587232, 0.580972, 0.579691, 0.574139, 0.567532,
    0.566006, 0.560921, 0.553889, 0.548597, 0.545865, 0.539851, 0.536447, 0.532176, 0.526217, 0.52128, 0.514403, 0.514091, 0.509272, 0.507629, 0.500514,
    0.49602, 0.49275, 0.485255, 0.481637, 0.477351, 0.472925, 0.46959, 0.46425, 0.459291, 0.456283, 0.452506, 0.448422, 0.448072, 0.440693, 0.439462,
    0.433776, 0.429185, 0.42583, 0.422193, 0.417554, 0.412196, 0.404759, 0.399625, 0.392681, 0.38872, 0.382111, 0.379972, 0.374079, 0.373424, 0.366812,
    0.365433, 0.360144, 0.355712, 0.352153
])
Bell_baffle_leakage_z_0_75 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.952164, 0.932054, 0.918775, 0.898166, 0.89158, 0.884084, 0.873337, 0.862164, 0.849748,
    0.841023, 0.827707, 0.821818, 0.817167, 0.80764, 0.798123, 0.79148, 0.784355, 0.778722, 0.769082, 0.759588, 0.752322, 0.751711, 0.742222, 0.733336,
    0.730403, 0.724627, 0.716983, 0.709925, 0.706578, 0.701202, 0.694408, 0.691425, 0.684748, 0.681776, 0.675771, 0.66987, 0.665387, 0.658756, 0.650396,
    0.642594, 0.63852, 0.633681, 0.630164, 0.623243, 0.620278, 0.614914, 0.608773, 0.60289, 0.599564, 0.592066, 0.587039, 0.580086, 0.579103, 0.571929,
    0.565004, 0.562871, 0.556585, 0.552183, 0.547073, 0.542175, 0.535473, 0.531288, 0.526005, 0.518616, 0.51564, 0.509016, 0.507369, 0.500113, 0.493584,
    0.491836, 0.485642, 0.477775, 0.471507, 0.468336, 0.461571, 0.457487, 0.452093, 0.445202, 0.43798, 0.428108, 0.42792, 0.424141, 0.421924, 0.414162,
    0.409255, 0.405735, 0.397827, 0.393402, 0.387784, 0.382579, 0.378578, 0.372665, 0.367707, 0.363647, 0.359545, 0.35391, 0.353453, 0.346015, 0.344783,
    0.336861, 0.331413, 0.328057, 0.323694, 0.318544, 0.312629, 0.303584, 0.297808, 0.289997, 0.285542, 0.279346, 0.275077, 0.267704, 0.266945,
    0.259507, 0.257888, 0.251468, 0.246404, 0.242337
])
Bell_baffle_leakage_z_1 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.934094, 0.899408, 0.88689, 0.864752, 0.855175, 0.846, 0.832233, 0.820088, 0.811664, 0.80142,
    0.78835, 0.781726, 0.776483, 0.765313, 0.755385, 0.749603, 0.742282, 0.73553, 0.725889, 0.716396, 0.709586, 0.709021, 0.698593, 0.690044, 0.686691,
    0.680127, 0.67261, 0.665553, 0.662016, 0.655963, 0.648118, 0.644201, 0.635976, 0.63258, 0.626768, 0.621075, 0.617208, 0.609726, 0.60012, 0.591542,
    0.587468, 0.582048, 0.578005, 0.570583, 0.567619, 0.561455, 0.554463, 0.548789, 0.545376, 0.537063, 0.531409, 0.523465, 0.522319, 0.51407, 0.508009,
    0.50576, 0.49867, 0.493705, 0.487867, 0.482187, 0.474436, 0.470146, 0.465546, 0.458712, 0.455268, 0.43738, 0.445348, 0.436779, 0.429227, 0.42748,
    0.42131, 0.413109, 0.406841, 0.403448, 0.395933, 0.391023, 0.38459, 0.37863, 0.372074, 0.361413, 0.360967, 0.356072, 0.353486, 0.344855, 0.339953,
    0.336008, 0.327035, 0.322011, 0.316393, 0.310588, 0.306074, 0.299769, 0.294481, 0.290318, 0.285397, 0.279684, 0.279195, 0.271757, 0.27035, 0.261526,
    0.255964, 0.252562, 0.248199, 0.241338, 0.234956, 0.226232, 0.219861, 0.210806, 0.205706, 0.197321, 0.194638, 0.187568, 0.186719, 0.178183,
    0.176295, 0.168945, 0.16388, 0.160321
])

Bell_baffle_leakage_zs = np.array([Bell_baffle_leakage_z_0, Bell_baffle_leakage_z_0_25, Bell_baffle_leakage_z_0_5, Bell_baffle_leakage_z_0_75, Bell_baffle_leakage_z_1]).T
Bell_baffle_leakage_z_values = np.array([0, .25, .5, .75, 1])

Bell_baffle_leakage_obj = RectBivariateSpline(Bell_baffle_leakage_x, Bell_baffle_leakage_z_values, Bell_baffle_leakage_zs, kx=3, ky=1, s=0.002)
'''Note: The smoothing factor was hand tuned to not overfit from points which 
were clearly wrong in the digitization. It will predict values above 1 however
for some values; this must be checked!
'''
Bell_baffle_leakage_x_max = Bell_baffle_leakage_x[-1]

#for ys in Bell_baffle_leakage_zs.T:
#    plt.plot(Bell_baffle_leakage_x, ys)
#for z in Bell_baffle_leakage_z_values:
#    xs = np.linspace(min(Bell_baffle_leakage_x), max(Bell_baffle_leakage_x), 1000)
#    ys = np.clip(Bell_baffle_leakage_obj(xs, z), 0, 1)
#    plt.plot(xs, ys, '--')

def baffle_leakage_Bell(Ssb, Stb, Sm):
    r'''Calculate the baffle leakage factor `Jl` which accounts for
    leakage between each baffle.
    
    Parameters
    ----------
    Ssb : float
        Shell to baffle leakage area, [m^2]
    Stb : float
        Total baffle leakage area, [m^2]
    Sm : float
        Crossflow area, [m^2]

    Returns
    -------
    Jl : float
        Baffle leakage factor in the Bell-Delaware method, [-]

    Notes
    -----
    Takes ~5 us per call, and 600 us to construct the spline.
    If the `x` parameter is larger than 0.743614, it is clipped to it.
        
    Examples
    --------
    >>> baffle_leakage_Bell(1, 3, 8)
    0.5906621282470395
    
    References
    ----------
    .. [1] Bell, Kenneth J. Final Report of the Cooperative Research Program on
       Shell and Tube Heat Exchangers. University of Delaware, Engineering
       Experimental Station, 1963.
    .. [2] Bell, Kenneth J. Delaware Method for Shell-Side Design. In Heat  
       Transfer Equipment Design, by Shah, R.  K., Eleswarapu Chinna Subbarao,
       and R. A. Mashelkar. CRC Press, 1988.
    .. [3] Green, Don, and Robert Perry. Perry's Chemical Engineers' Handbook,
       Eighth Edition. McGraw-Hill Professional, 2007.
    '''
    x = (Ssb + Stb)/Sm
    if x > Bell_baffle_leakage_x_max:
        x = Bell_baffle_leakage_x_max
    y = Ssb/(Ssb + Stb)
    if y > 1 or y < 0:
        raise ValueError('Ssb/(Ssb + Stb) must be between 0 and 1')
    Jl = Bell_baffle_leakage_obj(x, y)
    return min(float(Jl), 1.0)

Bell_bundle_bypass_x = np.array([0.0, 1e-5, 1e-4, 1e-3, 0.0388568, 0.0474941, 0.0572083, 0.0807999, 0.0915735, 0.0959337, 0.118724, 0.128469, 0.134716,
    0.142211, 0.146821, 0.156504, 0.162821, 0.169488, 0.178126, 0.185301, 0.194997, 0.200798, 0.210512, 0.212373, 0.221063, 0.222122, 0.228864,
    0.232856, 0.238578, 0.242605, 0.250104, 0.257958, 0.262866, 0.268403, 0.273639, 0.280289, 0.284999, 0.291067, 0.295186, 0.30005, 0.309764, 0.312548,
    0.31468, 0.320144, 0.323405, 0.328111, 0.33213, 0.333111, 0.33857, 0.341836, 0.343889, 0.349352, 0.351401, 0.35359, 0.359058, 0.361102, 0.366408,
    0.370597, 0.375601, 0.379541, 0.382811, 0.386913, 0.392363, 0.39766, 0.401106, 0.401841, 0.410811, 0.412615, 0.419939, 0.421633, 0.42633, 0.431067,
    0.434967, 0.440908, 0.444682, 0.450614, 0.45373, 0.457036, 0.462565, 0.464508, 0.47016, 0.47227, 0.477519, 0.480474, 0.482794, 0.486874, 0.490639,
    0.492758, 0.499075, 0.501281, 0.506824, 0.5116, 0.51494, 0.52159, 0.52187, 0.530498, 0.532368, 0.537013, 0.541276, 0.542244, 0.546385, 0.551805,
    0.553801, 0.5575, 0.562325, 0.56668, 0.568283, 0.572153, 0.576377, 0.580676, 0.582252, 0.5886, 0.591953, 0.599019, 0.601715, 0.602385, 0.610103,
    0.612441, 0.613194, 0.62061, 0.622146, 0.622934, 0.630324, 0.631852, 0.633669, 0.637109, 0.64136, 0.644447, 0.647887, 0.649879, 0.652335, 0.656363,
    0.657593, 0.661839, 0.665333, 0.667924, 0.672258, 0.674841, 0.678694, 0.681955, 0.685396, 0.688789, 0.69198, 0.69532
])
Bell_bundle_bypass_x_max = float(Bell_bundle_bypass_x[-1])
Bell_bundle_bypass_z_values = np.array([0.0, 0.05, 0.1, 1.0 / 6.0, 0.3, 0.5])

Bell_bundle_bypass_z_high_0_5 = np.ones(144)
Bell_bundle_bypass_z_high_0_3 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.990537, 0.988984, 0.98724, 0.983016, 0.980614, 0.979535, 0.974346, 0.972054, 0.970522,
    0.968688, 0.967675, 0.965549, 0.964164, 0.963959, 0.963171, 0.961603, 0.959253, 0.959162, 0.957048, 0.956644, 0.954757, 0.954523, 0.9529, 0.95197,
    0.950734, 0.949953, 0.951574, 0.949936, 0.947587, 0.946396, 0.945271, 0.943845, 0.942835, 0.941537, 0.940656, 0.940788, 0.942546, 0.940563,
    0.939047, 0.935797, 0.935104, 0.934105, 0.933252, 0.933045, 0.931888, 0.931164, 0.930682, 0.9294, 0.929485, 0.929948, 0.931104, 0.931397, 0.928907,
    0.926946, 0.925893, 0.925065, 0.924344, 0.923388, 0.922149, 0.92104, 0.92032, 0.920166, 0.918293, 0.917917, 0.917341, 0.917207, 0.916838, 0.916466,
    0.916159, 0.915693, 0.915397, 0.914931, 0.914687, 0.914428, 0.913994, 0.913842, 0.91334, 0.912902, 0.911815, 0.911203, 0.91078, 0.910038, 0.909353,
    0.908968, 0.907821, 0.907421, 0.906416, 0.905551, 0.904947, 0.903745, 0.903694, 0.902137, 0.9018, 0.900963, 0.900195, 0.900021, 0.899276, 0.898303,
    0.897944, 0.897281, 0.896416, 0.895636, 0.895349, 0.894656, 0.893901, 0.893133, 0.892852, 0.89172, 0.891122, 0.889865, 0.889385, 0.889266, 0.887895,
    0.88748, 0.887347, 0.887002, 0.887002, 0.887002, 0.886113, 0.885805, 0.88544, 0.884748, 0.883894, 0.883275, 0.882575, 0.882132, 0.881585, 0.880689,
    0.880426, 0.879577, 0.878879, 0.878362, 0.878362, 0.878362, 0.878362, 0.877712, 0.877026, 0.87635, 0.875715, 0.875051
])
Bell_bundle_bypass_z_high_0_167 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.98326, 0.97947, 0.974498, 0.962528, 0.957986, 0.956693, 0.949964, 0.947102, 0.945271,
    0.94206, 0.94009, 0.935965, 0.93353, 0.932117, 0.928823, 0.925995, 0.923086, 0.921351, 0.918452, 0.917897, 0.915313, 0.914999, 0.913, 0.911818,
    0.910127, 0.90895, 0.907403, 0.905106, 0.903391, 0.90146, 0.899637, 0.897328, 0.895696, 0.893598, 0.892176, 0.8905, 0.886812, 0.885691, 0.884834,
    0.882399, 0.880948, 0.879769, 0.878966, 0.87877, 0.87685, 0.875407, 0.874501, 0.873182, 0.872775, 0.872342, 0.870581, 0.869774, 0.86768, 0.865848,
    0.863665, 0.862771, 0.862131, 0.861322, 0.859193, 0.857129, 0.859086, 0.858609, 0.852897, 0.852509, 0.850934, 0.85034, 0.848528, 0.846705, 0.845041,
    0.842545, 0.841823, 0.840689, 0.839677, 0.838418, 0.836305, 0.835485, 0.833106, 0.832278, 0.831286, 0.830728, 0.830291, 0.828583, 0.827011,
    0.826114, 0.823157, 0.822169, 0.82102, 0.820047, 0.819426, 0.818189, 0.818085, 0.814886, 0.814194, 0.812289, 0.810543, 0.810058, 0.806263, 0.806263,
    0.806263, 0.806137, 0.804373, 0.802783, 0.802256, 0.801473, 0.800619, 0.799812, 0.799526, 0.798328, 0.796926, 0.793982, 0.792861, 0.792583,
    0.789808, 0.78897, 0.788701, 0.787226, 0.786921, 0.786757, 0.784122, 0.783578, 0.782932, 0.781709, 0.780202, 0.779109, 0.778433, 0.778042, 0.77756,
    0.776422, 0.775988, 0.774494, 0.77333, 0.772824, 0.77198, 0.771442, 0.770094, 0.768954, 0.767753, 0.766571, 0.765461, 0.764301
])
Bell_bundle_bypass_z_high_0_1 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.978035, 0.974378, 0.970282, 0.960405, 0.955928, 0.953958, 0.941171, 0.935756, 0.932301,
    0.928172, 0.925642, 0.92035, 0.916913, 0.9133, 0.908641, 0.904789, 0.899741, 0.89745, 0.893627, 0.892897, 0.889494, 0.88908, 0.886716, 0.885913,
    0.884594, 0.881903, 0.877493, 0.874369, 0.87224, 0.869806, 0.867741, 0.865076, 0.863023, 0.86048, 0.858872, 0.856977, 0.853205, 0.851584, 0.850211,
    0.846705, 0.845452, 0.843647, 0.842058, 0.841641, 0.839327, 0.837996, 0.837215, 0.835141, 0.834364, 0.833443, 0.831147, 0.830291, 0.828293,
    0.826718, 0.824687, 0.82305, 0.821515, 0.819223, 0.816189, 0.814075, 0.812703, 0.81241, 0.808849, 0.808135, 0.805242, 0.804574, 0.802726, 0.800866,
    0.799338, 0.797016, 0.795545, 0.793199, 0.791952, 0.790633, 0.78865, 0.787955, 0.785378, 0.784125, 0.781018, 0.779971, 0.779149, 0.777707, 0.776379,
    0.775632, 0.77341, 0.77338, 0.770144, 0.767521, 0.766358, 0.764048, 0.763944, 0.760626, 0.759946, 0.758344, 0.756878, 0.756543, 0.754964, 0.752903,
    0.752217, 0.750955, 0.749311, 0.74768, 0.747075, 0.745618, 0.743505, 0.741332, 0.740537, 0.738255, 0.737132, 0.731632, 0.729296, 0.729296, 0.729296,
    0.728522, 0.728273, 0.725825, 0.725318, 0.725059, 0.72263, 0.722122, 0.72146, 0.720209, 0.718666, 0.71766, 0.716539, 0.715891, 0.715086, 0.713635,
    0.713192, 0.711666, 0.708853, 0.706773, 0.705828, 0.705414, 0.704797, 0.703715, 0.702494, 0.701293, 0.700165, 0.698986
])
Bell_bundle_bypass_z_high_0_05 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.972281, 0.967922, 0.961369, 0.943692, 0.935729, 0.932525, 0.915956, 0.908961,
    0.906104, 0.904563, 0.901473, 0.895196, 0.891354, 0.885977, 0.87906, 0.874187, 0.86913, 0.86655, 0.862245, 0.861423, 0.857594, 0.857129, 0.852769,
    0.850462, 0.848255, 0.846705, 0.842424, 0.837963, 0.835187, 0.832066, 0.829126, 0.825407, 0.822783, 0.819415, 0.817095, 0.814308, 0.808771, 0.80719,
    0.805982, 0.802895, 0.801058, 0.798414, 0.796163, 0.795615, 0.79257, 0.79081, 0.789705, 0.786773, 0.785555, 0.784255, 0.781018, 0.780293, 0.778416,
    0.776757, 0.773823, 0.77152, 0.769804, 0.767657, 0.764814, 0.76206, 0.760275, 0.759852, 0.754714, 0.753788, 0.750038, 0.749171, 0.746514, 0.743844,
    0.742476, 0.740476, 0.738142, 0.733741, 0.732227, 0.731129, 0.729296, 0.728224, 0.725118, 0.723961, 0.721379, 0.719929, 0.718793, 0.716592,
    0.714554, 0.71341, 0.709585, 0.708255, 0.706445, 0.704915, 0.703256, 0.699727, 0.699579, 0.694462, 0.693873, 0.692411, 0.691072, 0.690566, 0.688406,
    0.685632, 0.684701, 0.682979, 0.68071, 0.678471, 0.677649, 0.675704, 0.673763, 0.671794, 0.671073, 0.668927, 0.667797, 0.664237, 0.662887, 0.662584,
    0.659112, 0.658063, 0.657689, 0.65401, 0.65325, 0.652861, 0.649222, 0.648472, 0.647937, 0.646926, 0.645678, 0.64442, 0.642745, 0.641777, 0.640586,
    0.638832, 0.638297, 0.636454, 0.634836, 0.633593, 0.631519, 0.630382, 0.628731, 0.627336, 0.626066, 0.624995, 0.62399, 0.622939
])
Bell_bundle_bypass_z_high_0 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.952236, 0.940656, 0.929217, 0.902172, 0.890997, 0.886514, 0.863444, 0.851755, 0.845079,
    0.837139, 0.832293, 0.822203, 0.816984, 0.810801, 0.80192, 0.794615, 0.78485, 0.779066, 0.769592, 0.767791, 0.759517, 0.758605, 0.752824, 0.749047,
    0.743669, 0.739906, 0.73295, 0.725735, 0.722154, 0.717987, 0.713174, 0.707108, 0.702842, 0.697384, 0.693703, 0.689382, 0.680999, 0.678318, 0.676273,
    0.671537, 0.669333, 0.666165, 0.662801, 0.661983, 0.657447, 0.654748, 0.653057, 0.648578, 0.646907, 0.645126, 0.640517, 0.638664, 0.634016,
    0.631344, 0.628167, 0.625058, 0.622488, 0.619125, 0.614363, 0.610288, 0.607796, 0.607265, 0.60083, 0.599544, 0.59421, 0.592943, 0.589445, 0.585503,
    0.582277, 0.577936, 0.575196, 0.571767, 0.569973, 0.567464, 0.563036, 0.561619, 0.557635, 0.556155, 0.55249, 0.550438, 0.548878, 0.546625, 0.544554,
    0.543231, 0.538071, 0.536281, 0.532469, 0.529276, 0.527497, 0.523935, 0.52375, 0.518089, 0.516762, 0.513373, 0.51047, 0.509884, 0.507382, 0.504126,
    0.502932, 0.500727, 0.497867, 0.495143, 0.494144, 0.491733, 0.488799, 0.485831, 0.484868, 0.481006, 0.479285, 0.476413, 0.473514, 0.472869,
    0.469205, 0.468011, 0.467512, 0.462626, 0.461732, 0.461273, 0.457, 0.456012, 0.45484, 0.452628, 0.450352, 0.448953, 0.447398, 0.446281, 0.444731,
    0.442201, 0.44145, 0.439096, 0.437168, 0.435842, 0.433942, 0.432813, 0.430923, 0.429157, 0.427301, 0.425479, 0.423772, 0.421993
])
Bell_bundle_bypass_z_high = np.array([Bell_bundle_bypass_z_high_0, Bell_bundle_bypass_z_high_0_05, Bell_bundle_bypass_z_high_0_1, Bell_bundle_bypass_z_high_0_167, Bell_bundle_bypass_z_high_0_3, Bell_bundle_bypass_z_high_0_5]).T
Bell_bundle_bypass_high_obj = RectBivariateSpline(Bell_bundle_bypass_x, Bell_bundle_bypass_z_values, Bell_bundle_bypass_z_high, kx = 3, ky = 3, s = 0.0007)

#for ys in Bell_bundle_bypass_z_high.T:
#    plt.plot(Bell_bundle_bypass_x, ys)
#    
#for z in Bell_bundle_bypass_z_values:
#    xs = np.linspace(min(Bell_bundle_bypass_x), max(Bell_bundle_bypass_x), 1000)
#    ys = np.clip(Bell_bundle_bypass_high_obj(xs, z), 0, 1)
#    plt.plot(xs, ys, '--')
#plt.show()

Bell_bundle_bypass_z_low_0_5 = Bell_bundle_bypass_z_high_0_5
Bell_bundle_bypass_z_low_0_3 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.991796, 0.989982, 0.987945, 0.983016, 0.980614, 0.979535, 0.974346, 0.972054, 0.970522,
    0.968688, 0.967675, 0.965549, 0.964164, 0.963959, 0.963171, 0.961603, 0.959253, 0.959162, 0.957048, 0.956644, 0.954757, 0.954523, 0.9529, 0.95197,
    0.950734, 0.949953, 0.951574, 0.949936, 0.947587, 0.946396, 0.945271, 0.943845, 0.942835, 0.941537, 0.940656, 0.940788, 0.942546, 0.940563,
    0.939047, 0.935797, 0.935104, 0.934105, 0.933252, 0.933045, 0.931888, 0.931164, 0.930682, 0.9294, 0.929485, 0.929948, 0.931104, 0.931397, 0.928907,
    0.926946, 0.925893, 0.925065, 0.924344, 0.923388, 0.922112, 0.920852, 0.920034, 0.919859, 0.917732, 0.917305, 0.915572, 0.915172, 0.914063,
    0.912946, 0.912028, 0.910631, 0.909744, 0.908352, 0.907622, 0.906848, 0.905555, 0.905101, 0.903781, 0.903289, 0.902066, 0.901379, 0.900839,
    0.899919, 0.899149, 0.898717, 0.897483, 0.897083, 0.89608, 0.895216, 0.894613, 0.893412, 0.893362, 0.891807, 0.89147, 0.890635, 0.889868, 0.889694,
    0.888923, 0.887829, 0.887427, 0.886681, 0.88571, 0.884834, 0.884477, 0.883613, 0.882672, 0.881954, 0.881691, 0.880632, 0.880073, 0.878897, 0.878448,
    0.878332, 0.876793, 0.876328, 0.876178, 0.874703, 0.874398, 0.874242, 0.872631, 0.872295, 0.871914, 0.871488, 0.870962, 0.87058, 0.870155, 0.869909,
    0.869486, 0.868691, 0.868448, 0.867611, 0.866922, 0.866412, 0.86556, 0.864996, 0.864155, 0.863444, 0.86277, 0.862105, 0.86148, 0.860827
])
Bell_bundle_bypass_z_low_0_167 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.980974, 0.977905, 0.97446, 0.966143, 0.962368, 0.960686, 0.951112, 0.947048, 0.944452,
    0.941346, 0.939441, 0.935452, 0.93269, 0.92946, 0.925293, 0.921845, 0.917207, 0.914443, 0.909833, 0.908959, 0.905975, 0.905612, 0.903304, 0.90194,
    0.899989, 0.898618, 0.896071, 0.893412, 0.891754, 0.889887, 0.887916, 0.885239, 0.883183, 0.880493, 0.879259, 0.877803, 0.874903, 0.874074,
    0.873134, 0.870731, 0.869578, 0.868649, 0.867856, 0.867642, 0.865256, 0.863831, 0.862988, 0.860849, 0.860049, 0.859186, 0.856524, 0.855531,
    0.852959, 0.852139, 0.851171, 0.84986, 0.848459, 0.846705, 0.844612, 0.842583, 0.841212, 0.840919, 0.837359, 0.836645, 0.833751, 0.833084, 0.831743,
    0.830749, 0.829968, 0.828849, 0.827989, 0.825515, 0.824217, 0.822981, 0.820918, 0.820193, 0.817941, 0.817102, 0.815018, 0.813871, 0.813014,
    0.811509, 0.810137, 0.809474, 0.8075, 0.806811, 0.805085, 0.8036, 0.802563, 0.800503, 0.800417, 0.797752, 0.797175, 0.795746, 0.794422, 0.794073,
    0.792581, 0.790633, 0.789837, 0.788364, 0.786627, 0.785849, 0.785563, 0.784873, 0.783229, 0.781532, 0.780917, 0.778551, 0.777304, 0.774683,
    0.773686, 0.773438, 0.772069, 0.771659, 0.771527, 0.768654, 0.768059, 0.767753, 0.765181, 0.764651, 0.76402, 0.76335, 0.762532, 0.76154, 0.75956,
    0.758417, 0.757994, 0.757301, 0.757089, 0.75611, 0.754779, 0.753793, 0.752544, 0.752102, 0.751445, 0.750747, 0.749575, 0.748421, 0.747337, 0.746205
])
Bell_bundle_bypass_z_low_0_1 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.978947, 0.974857, 0.970278, 0.959247, 0.954251, 0.952236, 0.938267, 0.932356, 0.928587,
    0.924085, 0.921326, 0.915559, 0.911816, 0.907882, 0.902811, 0.89862, 0.892988, 0.889635, 0.885582, 0.884834, 0.879037, 0.878345, 0.87566, 0.874074,
    0.87124, 0.869251, 0.86556, 0.862478, 0.860473, 0.858072, 0.85515, 0.850859, 0.849041, 0.846705, 0.844334, 0.841542, 0.835995, 0.834411, 0.833976,
    0.832942, 0.832325, 0.829367, 0.82685, 0.826237, 0.824191, 0.82297, 0.822203, 0.81994, 0.819093, 0.818189, 0.815149, 0.814015, 0.81124, 0.809258,
    0.806898, 0.805045, 0.80351, 0.801588, 0.799042, 0.796575, 0.794975, 0.794634, 0.791377, 0.790729, 0.787823, 0.78715, 0.784863, 0.782599, 0.781214,
    0.779109, 0.776888, 0.77341, 0.772317, 0.771158, 0.769179, 0.768425, 0.766237, 0.765263, 0.762533, 0.761, 0.759834, 0.757882, 0.756085, 0.755076,
    0.752075, 0.751029, 0.749142, 0.747519, 0.746277, 0.743778, 0.743677, 0.740769, 0.74014, 0.737582, 0.735207, 0.73467, 0.733289, 0.731487, 0.730713,
    0.728963, 0.726686, 0.724636, 0.723901, 0.722489, 0.720951, 0.719026, 0.718255, 0.715157, 0.713949, 0.711376, 0.710288, 0.710018, 0.706915,
    0.705978, 0.705676, 0.702713, 0.7021, 0.701786, 0.698849, 0.698244, 0.697524, 0.696164, 0.694821, 0.693848, 0.692765, 0.691722, 0.690438, 0.688338,
    0.687698, 0.686042, 0.684684, 0.683677, 0.681998, 0.680999, 0.680403, 0.679899, 0.679368, 0.677706, 0.676072, 0.674366
])
Bell_bundle_bypass_z_low_0_05 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.97132, 0.966107, 0.959971, 0.942755, 0.934996, 0.931875, 0.915726, 0.908906, 0.906104,
    0.904563, 0.901473, 0.895196, 0.891354, 0.885977, 0.87906, 0.874187, 0.867386, 0.86321, 0.856262, 0.854938, 0.84878, 0.848124, 0.843964, 0.841509,
    0.838004, 0.835546, 0.830988, 0.826241, 0.823289, 0.81997, 0.816844, 0.812892, 0.810104, 0.806526, 0.804106, 0.801259, 0.795601, 0.793967, 0.792688,
    0.789419, 0.787596, 0.785077, 0.782932, 0.782351, 0.779127, 0.777205, 0.776119, 0.773238, 0.77216, 0.770953, 0.767771, 0.766585, 0.763514, 0.761099,
    0.758428, 0.756396, 0.754714, 0.752376, 0.749281, 0.745922, 0.743739, 0.743322, 0.738296, 0.737388, 0.73372, 0.732874, 0.730275, 0.727663, 0.725519,
    0.722266, 0.720207, 0.716983, 0.715295, 0.713509, 0.710531, 0.709487, 0.70646, 0.705709, 0.703842, 0.702816, 0.702076, 0.700776, 0.699579, 0.698012,
    0.693361, 0.691743, 0.687698, 0.686208, 0.685168, 0.682279, 0.682134, 0.677697, 0.676739, 0.674366, 0.671761, 0.671172, 0.668654, 0.666449,
    0.665778, 0.664536, 0.662357, 0.660396, 0.659676, 0.657624, 0.655391, 0.653126, 0.652298, 0.648972, 0.647223, 0.643551, 0.642155, 0.64196, 0.639714,
    0.639035, 0.638682, 0.635109, 0.634371, 0.633993, 0.63046, 0.629731, 0.628867, 0.627232, 0.625218, 0.62376, 0.622139, 0.621202, 0.62005, 0.618248,
    0.617731, 0.615947, 0.614484, 0.61328, 0.611273, 0.61008, 0.608305, 0.606806, 0.605229, 0.603678, 0.602222, 0.600702
])
Bell_bundle_bypass_z_low_0 = np.array([1.0, 0.99999, 0.9999, 0.999, 0.952236, 0.940656, 0.929217, 0.90002, 0.886521, 0.880701, 0.850893, 0.838458, 0.831886,
    0.823549, 0.818189, 0.807989, 0.801404, 0.794512, 0.78485, 0.776988, 0.766488, 0.760275, 0.751029, 0.749052, 0.740111, 0.739124, 0.732874, 0.729198,
    0.723961, 0.720158, 0.713129, 0.705842, 0.701326, 0.696132, 0.690988, 0.684186, 0.679334, 0.67352, 0.66971, 0.665448, 0.657018, 0.654621, 0.652811,
    0.648334, 0.645676, 0.641432, 0.637791, 0.636967, 0.632602, 0.630005, 0.628212, 0.623369, 0.621616, 0.619905, 0.61565, 0.61403, 0.609576, 0.606083,
    0.601936, 0.598691, 0.596011, 0.592666, 0.588251, 0.583992, 0.581238, 0.580668, 0.574145, 0.572724, 0.566812, 0.565183, 0.56069, 0.556978, 0.55452,
    0.550223, 0.547289, 0.543116, 0.540988, 0.538616, 0.534414, 0.532944, 0.528694, 0.527116, 0.523265, 0.521112, 0.519429, 0.516481, 0.514038,
    0.512668, 0.508511, 0.507017, 0.503284, 0.500089, 0.497867, 0.493714, 0.49354, 0.487757, 0.486467, 0.482972, 0.479717, 0.478981, 0.476477, 0.473881,
    0.472928, 0.470456, 0.467252, 0.464687, 0.46375, 0.461495, 0.458195, 0.45486, 0.453935, 0.45032, 0.448303, 0.443758, 0.442035, 0.441609, 0.437337,
    0.436027, 0.435562, 0.431011, 0.430169, 0.429742, 0.425761, 0.424942, 0.423971, 0.422137, 0.42001, 0.418705, 0.417255, 0.416416, 0.414108, 0.41035,
    0.409842, 0.408091, 0.406656, 0.405331, 0.402949, 0.401536, 0.399438, 0.39767, 0.395938, 0.394249, 0.392668, 0.391019
])
Bell_bundle_bypass_z_low = np.array([Bell_bundle_bypass_z_low_0, Bell_bundle_bypass_z_low_0_05, Bell_bundle_bypass_z_low_0_1, Bell_bundle_bypass_z_low_0_167, Bell_bundle_bypass_z_low_0_3, Bell_bundle_bypass_z_low_0_5]).T
Bell_bundle_bypass_low_obj = RectBivariateSpline(Bell_bundle_bypass_x, Bell_bundle_bypass_z_values, Bell_bundle_bypass_z_low, kx = 3, ky = 3, s = 0.0007)

#for ys in Bell_bundle_bypass_z_low.T:
#    plt.plot(Bell_bundle_bypass_x, ys)
#    
#for z in Bell_bundle_bypass_z_values:
#    xs = np.linspace(min(Bell_bundle_bypass_x), max(Bell_bundle_bypass_x), 1000)
#    ys = np.clip(Bell_bundle_bypass_low_obj(xs, z), 0, 1)
#    plt.plot(xs, ys, '--')
#plt.show()


def bundle_bypassing_Bell(bypass_area_fraction, seal_strips, crossflow_rows,
                          laminar=False):
    r'''Calculate the bundle bypassing effect `Jb` according to the 
    Bell-Delaware method for heat exchanger design.   
        
    Parameters
    ----------
    bypass_area_fraction : float
        Fraction of the crossflow area which is not blocked by a baffle or 
        anything else and available for bypassing, [-]
    seal_strips : int
        Number of seal strips per side of a baffle added to prevent bypassing,
        [-]
    crossflow_rows : int
        The number of tube rows in the crosslfow of the baffle, [-]
    laminar : bool
        Whether to use the turbulent correction values or the laminar ones;
        the Bell-Delaware method uses a Re criteria of 100 for this, [-]

    Returns
    -------
    Jb : float
        Bundle bypassing effect correction factor in the Bell-Delaware method, 
        [-]

    Notes
    -----
    Takes ~5 us per call, and 1.2 ms to construct both the turbulent and
    laminar splines.
    If the `bypass_area_fraction` parameter is larger than 0.695, it is clipped
    to it.

    Examples
    --------
    >>> bundle_bypassing_Bell(0.5, 5, 25)
    0.8469611760884599
    >>> bundle_bypassing_Bell(0.5, 5, 25, laminar=True)
    0.8327442867825271
    
    References
    ----------
    .. [1] Bell, Kenneth J. Final Report of the Cooperative Research Program on
       Shell and Tube Heat Exchangers. University of Delaware, Engineering
       Experimental Station, 1963.
    .. [2] Bell, Kenneth J. Delaware Method for Shell-Side Design. In Heat  
       Transfer Equipment Design, by Shah, R.  K., Eleswarapu Chinna Subbarao,
       and R. A. Mashelkar. CRC Press, 1988.
    .. [3] Green, Don, and Robert Perry. Perry's Chemical Engineers' Handbook,
       Eighth Edition. McGraw-Hill Professional, 2007.
    '''
    z = seal_strips/crossflow_rows
    x = bypass_area_fraction
    
    obj = Bell_bundle_bypass_low_obj if laminar else Bell_bundle_bypass_high_obj
    
    if x > Bell_bundle_bypass_x_max:
        x = Bell_bundle_bypass_x_max
        
    Jb = obj(x, z)
    return min(float(Jb), 1.0)
