# CubiCal: a radio interferometric calibration suite
# (c) 2017 Rhodes University & Jonathan S. Kenyon
# http://github.com/ratt-ru/CubiCal
# This code is distributed under the terms of GPLv2, see LICENSE.md for details
"""
Cython kernels for the full-complex 2x2 gain machine. Functions require output arrays to be 
provided. Common dimensions of arrays are:

+----------------+------+
| Dimension      | Size |
+================+======+
| Direction      |   d  |
+----------------+------+
| Model          |   m  |
+----------------+------+
| Time           |   t  |
+----------------+------+
| Time Intervals |   ti |
+----------------+------+
| Frequency      |   f  |
+----------------+------+
| Freq Intervals |   fi |
+----------------+------+
| Antenna        |   a  |
+----------------+------+
| Correlation    |   c  |
+----------------+------+

"""

import numpy as np
cimport numpy as np
import cython
from cython.parallel import parallel, prange
import cubical.kernels

# pull in standard inlined matrix operations
include "includes/matrix_ops.pxi"

# now, define which set of operations to use in this kernel. The idea is, the set of inlined functions below
# determine whether we're dealing with diagonal or full 2x2 matrices -- these functions will be defined
# differently for the full_complex, diag_complex and diagdiag_complex kernels. The actual kernel methods
# themselves are written in terms of these functions -- they're pulled in from complex_gain_kernel.pxi below


cdef inline void mat_product_gm(complex3264a *out,complex3264 *g,complex3264a *m) nogil:
    """
    Computes a 2x2 matrix product: out = G.M. G is diagonal.
    """
    out[0] = g[0]*m[0]
    out[1] = g[0]*m[1]
    out[2] = g[3]*m[2]
    out[3] = g[3]*m[3]

cdef inline void mat_product_update(complex3264 * out,const complex3264 *a,const complex3264 *b) nogil:
    """
    This is used for the (J^HR)(J^HJ)^{-1} product.
    """
    out[0] = (a[0]*b[0] + a[1]*b[2])
    out[1] = out[2] = 0
    out[3] = (a[2]*b[1] + a[3]*b[3])

cdef inline void add_rjh_product(complex3264 * out,const vcomplex *r,const vcomplex *jh) nogil:
    """
    Adds a 2x2 matrix product in place: out += R.J
    """
    out[0] += (r[0]*jh[0] + r[1]*jh[2])
    out[1] += (r[0]*jh[1] + r[1]*jh[3])
    out[2] += (r[2]*jh[0] + r[3]*jh[2])
    out[3] += (r[2]*jh[1] + r[3]*jh[3])

cdef inline void add_jhj_product(complex3264 * out,const vcomplex *j) nogil:
    """
    Adds a matrix conjugate product in place: out += J^H.J
    """
    out[0] += (j[0].conjugate()*j[0] + j[2].conjugate()*j[2])
    out[1] += (j[0].conjugate()*j[1] + j[2].conjugate()*j[3])
    out[2] += (j[1].conjugate()*j[0] + j[3].conjugate()*j[2])
    out[3] += (j[1].conjugate()*j[1] + j[3].conjugate()*j[3])

cdef inline void gmgh_product(vcomplex * out,const complex3264 *g,const vcomplex *m,const complex3264 *gh) nogil:
    """
    Computes a triple 2x2 matrix product: out = G.M.G^H
    """
    out[0] = g[0]*m[0]*gh[0]
    out[1] = g[0]*m[1]*gh[3]
    out[2] = g[3]*m[2]*gh[0]
    out[3] = g[3]*m[3]*gh[3]

cdef inline void subtract_gmgh_product(vcomplex * out,const complex3264 *g,const vcomplex *m,const complex3264 *gh) nogil:
    """
    Subtracts a triple 2x2 matrix product: out -= G.M.G^H
    """
    out[0] -= g[0]*m[0]*gh[0]
    out[1] -= g[0]*m[1]*gh[3]
    out[2] -= g[3]*m[2]*gh[0]
    out[3] -= g[3]*m[3]*gh[3]

cdef inline void inplace_gmgh_product(const complex3264 *g,vcomplex *m,const complex3264 *gh) nogil:
    """
    Computes a triple 2x2 matrix product in place: M = G.M.G^H
    """
    gmgh_product(m,g,m,gh)


cdef inline void inplace_left_product(const complex3264 *g,vcomplex *m) nogil:
    """
    Computes a triple 2x2 matrix product in place: M = G.M.G^H
    """
    m[0] *= g[0]
    m[1] *= g[0]
    m[2] *= g[3]
    m[3] *= g[3]

cdef inline void inplace_right_product(vcomplex *m,const complex3264 *g) nogil:
    """
    Computes a triple 2x2 matrix product in place: M = G.M.G^H
    """
    m[0] *= g[0]
    m[1] *= g[3]
    m[2] *= g[0]
    m[3] *= g[3]


cdef inline void vis_mat_conjugate(complex3264 * out,const complex3264 *x) nogil:
    mat_conjugate(out,x)



# pull in all the standard kernel method definitions

include "includes/complex_gain_kernel.pxi"

# map the J^H.J inversion method to a generic inversion

cycompute_jhjinv = cygenerics.cycompute_2x2_inverse

cyinvert_gains = cygenerics.cycompute_diag_inverse
