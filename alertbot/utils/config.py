# File For Storing External Data

es_impvol = None
nq_impvol = None
rty_impvol = None
cl_impvol = None
es_bias = None
nq_bias = None
rty_bias = None
cl_bias = None
es_swing_bias = None
nq_swing_bias = None
rty_swing_bias = None
cl_swing_bias = None
es_long_term_bias = None
nq_long_term_bias = None
rty_long_term_bias = None
cl_long_term_bias = None

def set_impvol(es, nq, rty, cl):
    global es_impvol, nq_impvol, rty_impvol, cl_impvol
    es_impvol = es
    nq_impvol = nq
    rty_impvol = rty
    cl_impvol = cl
    
def set_bias(es, nq, rty, cl):
    global es_bias, nq_bias, rty_bias, cl_bias
    es_bias = es
    nq_bias = nq
    rty_bias = rty
    cl_bias = cl
    
def set_swing_bias(es, nq, rty, cl):
    global es_swing_bias, nq_swing_bias, rty_swing_bias, cl_swing_bias
    es_swing_bias = es
    nq_swing_bias = nq
    rty_swing_bias = rty
    cl_swing_bias = cl    
    
def set_long_term_bias(es, nq, rty, cl):
    global es_long_term_bias, nq_long_term_bias, rty_long_term_bias, cl_long_term_bias
    es_long_term_bias = es
    nq_long_term_bias = nq
    rty_long_term_bias = rty
    cl_long_term_bias = cl       