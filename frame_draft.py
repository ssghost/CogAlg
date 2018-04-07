from scipy import misc
from collections import deque
import math as math
import numpy as np

''' core algorithm of levels 1 + 2, modified to process one image: find blobs and patterns in 2D frame.
    It performs several steps of encoding, incremental per scan line defined by vertical coordinate y:

    y: comp(p_): lateral pixel comp -> tuple t,
    y- 1: ycomp(t_): vertical pixel comp -> quadrant t2, 1D pattern P,  
    y- 2: scan_P_(P, _P) -> fork_, root_: finds vertical continuity between Ps of adjacent lines 
    y- 3+: incr_blob: merges Ps into 2D blob | term_blob: terminated blob orient and scan_Py_ -> 2D patterns PPs...

    Pixel comparison in 2D forms lateral and vertical derivatives: 2 matches and 2 differences per pixel. 
    They are formed on the same level because average lateral match ~ average vertical match.
    Pixels are discrete samples of continuous image, so rightward and downward derivatives per pixel are 
    equally representative samples of 0-90 degree quadrant gradient: minimal unique unit of 2D gradient. 
    Thus, quadrant gradient is estimated as the average of these two orthogonally diverging derivatives.
    Blob is contiguous area of same-sign quadrant gradient, of difference for dblob or match deviation for vblob.

    All 2D functions (ycomp, scan_P_, etc.) input two lines: higher and lower, convert elements of lower line 
    into elements of new higher line, and displace elements of old higher line into higher functions.
    Higher-line elements include additional variables, derived while they were lower-line elements.
    frame() is layered: partial lower functions can work without higher functions.
    None of this is tested, except as analogue functions in line_POC()  
    
    postfix '_' denotes array name, vs. same-name elements of that array 
    prefix '_' denotes higher-line variable or pattern '''


def comp(p_):  # comparison of consecutive pixels within a line forms tuples: pixel, match, difference

    t_ = []  # complete fuzzy tuples: summation range = rng
    it_ = deque(maxlen=rng)  # incomplete fuzzy tuples: summation range < rng

    for p in p_:
        index = 0

        for it in it_:  # incomplete tuples, with summation range from 0 to rng
            pri_p, fd, fm = it

            d = p - pri_p  # difference between pixels
            m = min(p, pri_p)  # match between pixels

            fd += d  # fuzzy d: sum of ds between p and all prior ps within it_
            fm += m  # fuzzy m: sum of ms between p and all prior ps within it_

            it_[index] = pri_p, fd, fm
            index += 1

        if len(it_) == rng:  # or while x < rng: icomp(){ p = pop(p_).., no t_.append?
            t_.append((pri_p, fd, fm))  # completed tuple is transferred from it_ to t_

        it_.appendleft((p, 0, 0))  # new prior tuple, fd and fm are initialized at 0

    t_ += it_  # last number = rng of tuples remain incomplete
    return t_


def ycomp(t_, t2__, _vP_, _dP_):  # vertical comparison between pixels of consecutive lines forms 2D tuples t2

    vP_ = []; vP = [0,0,0,0,0,0,0,0,[]]  # value pattern = pri_s, I, D, Dy, M, My, G, Olp, e_
    dP_ = []; dP = [0,0,0,0,0,0,0,0,[]]  # difference pattern = pri_s, I, D, Dy, M, My, G, Olp, e_

    vblob_, dblob_ = [],[]  # output line of vg- and dg- sign blobs, vertical concat -> frame in frame()

    x = 0; new_t2__ = []   # t2_ buffer: 2D array
    olp, ovG, odG = 0,0,0  # len of overlap between vP and dP, gs summed over olp, all shared

    for t, t2_ in zip(t_, t2__):  # compares vertically consecutive pixels, forms quadrant gradients
        p, d, m = t
        index = 0
        x += 1

        for t2 in t2_:
            pri_p, _d, fdy, _m, fmy = t2

            dy = p - pri_p  # vertical difference between pixels
            my = min(p, pri_p)  # vertical match between pixels

            fdy += dy  # fuzzy dy: sum of dys between p and all prior ps within t2_
            fmy += my  # fuzzy my: sum of mys between p and all prior ps within t2_

            t2_[index] = pri_p, _d, fdy, _m, fmy
            index += 1

        if len(t2_) == rng:  # or while y < rng: i_ycomp(): t2_ = pop(t2__), t = pop(t_)., no form_P?

            dg = _d + fdy  # d gradient
            vg = _m + fmy - ave  # v gradient
            t2 = pri_p, _d, fdy, _m, fmy  # completed 2D tuple moved from t2_ to form_P:

            # form 1D patterns vP and dP: horizontal spans of same-sign vg or dg, with associated vars:

            olp, ovG, odG, vP, dP, vP_, _vP_, vblob_ = form_P(1, t2, vg, dg, olp, ovG, odG, vP, dP, vP_, _vP_, vblob_, x)
            olp, odG, ovG, dP, vP, dP_, _dP_, dblob_ = form_P(0, t2, dg, vg, olp, odG, ovG, dP, vP, dP_, _dP_, dblob_, x)

        t2_.appendleft((p, d, 0, m, 0))  # initial fdy and fmy = 0, new t2 replaces completed t2 in t2_
        new_t2__.append(t2_)

    # line ends, vP and dP are terminated after inclusion of t2 with incomplete lateral fd and fm:

    if olp:  # if vP x dP overlap len > 0, incomplete vg - ave / (rng / X-x)?

        odG *= ave_k; odG = odG.astype(int)  # ave_k = V / I, to project V of odG

        if ovG > odG:  # comp of olp vG and olp dG, == goes to vP: secondary pattern?
            dP[7] += olp  # overlap of lesser-oG vP or dP, or P = P, Olp?
        else:
            vP[7] += olp  # to form rel_rdn = alt_rdn / len(e_)

    if y + 1 > rng:  # starting with the first line of complete t2s

        vP_, _vP_, vblob_ = scan_P_(0, vP, vP_, _vP_, vblob_, x)  # returns empty _vP_
        dP_, _dP_, dblob_ = scan_P_(1, dP, dP_, _dP_, dblob_, x)  # returns empty _dP_

    return new_t2__, _vP_, _dP_, vblob_, dblob_  # extended in scan_P_

    # poss alt_: top P alt = Olp, oG, alt_oG: to remove if hLe demotion and alt_oG < oG?
    # P_ can be redefined as np.array ([P, alt_, roots, forks) to increment without init?


def form_P(typ, t2, g, alt_g, olp, oG, alt_oG, P, alt_P, P_, _P_, blob_, x):

    # forms 1D dP or vP, then scan_P_ adds forks in _P fork_s and accumulates blob_

    p, d, dy, m, my = t2  # 2D tuple of quadrant variables per pixel
    pri_s, I, D, Dy, M, My, G, Olp, e_ = P  # initial pri_ vars = 0, or skip form?

    s = 1 if g > 0 else 0  # g = 0 is negative: no selection?
    if s != pri_s and x > rng + 2:  # P is terminated

        if typ: alt_oG *= ave_k; alt_oG = alt_oG.astype(int)  # ave V / I, to project V of odG
        else:   oG *= ave_k; oG = oG.astype(int)  # same for h_der and h_comp eval?

        if oG > alt_oG:  # comp between overlapping vG and dG
            Olp += olp  # olp is assigned to the weaker of P | alt_P, == -> P: local access
        else:
            alt_P[7] += olp

        P = (pri_s, I, D, Dy, M, My, G, Olp, e_), [], []  # no ave * alt_rdn / e_: adj < cost?
        P_, _P_, blob_ = scan_P_(typ, P, P_, _P_, blob_, x)  # P scans overlapping higher-line _Ps

        I, D, Dy, M, My, G, Olp, e_ = 0, 0, 0, 0, 0, 0, 0, []  # P initialization
        olp, oG, alt_oG = 0, 0, 0  # olp initialization

    # continued or initialized vars are accumulated (use zip S_vars?):

    olp += 1  # len of overlap to stronger alt-type P, accumulated until P or _P terminates
    oG += g; alt_oG += alt_g  # for eval to assign olp to alt_rdn of vP or dP

    I += p    # inputs and derivatives are summed within P for comp_P and orientation:
    D += d    # lateral D
    Dy += dy  # vertical D
    M += m    # lateral M
    My += my  # vertical M
    G += g    # d or v gradient summed to define P value, or V = M - 2a * W?

    e_.append(((p, d, dy, m, my), g, alt_g))  # | p, g, alt_g for vP | g for dP?
    # for incremental range | derivation comp, or selective oriented rescan

    P = [s, I, D, Dy, M, My, G, Olp, e_]

    return olp, oG, alt_oG, P, alt_P, P_, _P_, blob_  # accumulated in ycomp


def scan_P_(typ, P, P_, _P_, blob_, x):  # P scans shared-x_coord _Ps in _P_, forms overlapping Gs

    buff_ = []
    (s, I, D, Dy, M, My, G, Olp, e_), root_, root_sel_ = P  # roots are to find unique fork Ps

    ix = x - len(e_)  # initial x of P
    _ix = 0  # initialized ix of _P displaced from _P_ by last scan_P_

    while x >= _ix:  # P to _P match eval, while horizontal overlap between P and _P_:

        ex = x  # ex is lateral coordinate of loaded P element
        oG = 0  # fork gradient overlap: oG += g (distinct from alt_P' oG)
        _P, blob, fork_, fork_sel_ = _P_.popleft()  # _P in y-2, blob in y-3, forks in y-1

        if s == _P[0]:  # if s == _s: vg or dg sign match, fork_.append eval

            while ex > _P[1]:  # ex > _ix
                for e in e_:  # accumulation of oG between P and _P:

                    if typ: oG += e[1]  # if vP: e = p, g, alt_g
                    else: oG += e  # if dP: e = g
                    ex += 1  # odG is adjusted: *= ave_k in form_P

            if oG > ave * 16:  # if mult _P: cost of fork and blob in term_blob, unless fork_==1

                root_.append((oG, _P))  # _Ps connected to P, term if root_!= 1
                fork_.append((oG, P))  # Ps connected to _P, term if fork_!= 1

            elif oG > ave * 4:  # if one _P: > cost of summation in form_blob, unless root_!=1?

                root_sel_.append((oG, _P))  # _Ps connected to P, select root_.append at P output
                fork_sel_.append((oG, P))  # Ps connected to _P, select fork_.append at P output

        ''' eval for incremental orders of redundancy, added if frequently valuable:
            mono blob / max_filter, fork_ eval / n_filter, fork__ eval / nn_filter -> fork_ssel_..
        '''

        if _P[2] > ix:  # if _x > ix:
            buff_.append(_P)  # _P is buffered for scan_P_(next P)

        elif fork_ == 0 and fork_sel_ == 0:  # no overlap between _P and next P, term_blob,
            # else _P is buffered in fork Ps root_| root_sel_, term eval at P output

            blob = incr_blob((oG, _P), blob)  # default _P incl, empty init at final P root_!= 1:
            blob = term_blob(typ, blob)  # eval for orient(), incr_comp(), scan_Py_()
            blob_.append((blob, fork_))  # top-down fork_, no root_: redundant to fork_

    # no overlap between P and next _P, at next-line input: blob +=_P for root_ of P if fork_ != 0

    if root_ == 1 and root_[0][3] > 1:  # select single alt fork for single root, else split

        root_ = [max(root_sel_)]  # same as root = max(root_sel_, key= lambda sel_root: sel_root[0])
        root_[0][1].append((root_[0][0][0], P))  # _P(oG, P) is added to fork_ of max root _P

    for _P, blob, fork_, fork_sel_ in root_:  # final fork assignment and blob increment per _P

        blob = incr_blob(_P, blob)  # default per root, blob is modified in root _P?

        if fork_ == 1 and root_sel_ > 1:  # select single max root for single fork, else merge

            fork_ = [max(fork_sel_)]
            fork_[0][2].append(_P)  # _P(oG, _P) is added to root_ of max fork P

        if fork_ != 1 or root_ != 1:  # blob split | merge, also if y == Y - 1 in frame()?

            blob = term_blob(typ, blob)  # eval for orient(), incr_comp(), scan_Py_()
            blob_.append((blob, fork_))  # terminated blob_ is input line y - 3+ | record layer 5+

    if root_ == 1 and root_[0][3] == 1:  # blob assign if final P' root_==1 and root' fork_==1
        blob = root_[0][1]  # root' fork' blob
    else:
        blob = (0,0,0,0,0,0,0,0,0,0,[])  # init s, L2, I2, D2, Dy2, M2, My2, G2, OG, Olp2, Py_

    P = s, ix, x, I, D, Dy, M, My, G, Olp, e_  # P becomes _P, oG is per new P in fork_?

    P_.append((P, blob, [], []))  # blob assign, forks init, _P_ = P_ for next-line scan_P_()
    buff_ += _P_  # excluding displaced _Ps

    return P_, buff_, blob_  # _P_ = buff_ for scan_P_(next P)

''' sequential displacement and higher record-layer (L) inclusion at record layer's end:

    y, 1st 1L: p_ -> t_
    y- 1,  2L: t_, _t_ -> t2_ -> P_
    y- 2,  3L: P_, _P_ -> fork_ between _P and Ps
    y- 3+, 4L: fork_, blob_: continued blob segments of variable depth 
    y- 3+, 5+: blob_, term_: layers of terminated segments, composed of inputs from lines 3+  
    
    sum into fork network, global term if root_ == 0, same OG eval? also sum per frame? '''


def incr_blob(_P, blob):  # continued or initialized blob is incremented by attached _P, replace by zip?

    s, _x, _ix, _lx, Dx, L2, I2, D2, Dy2, M2, My2, G2, OG, Olp, Py_ = blob  # or S_par tuple?
    oG, (s, ix, lx, I, D, Dy, M, My, G, olp, e_) = _P  # s is re-assigned, ix and lx from scan_P_

    x = lx - len(e_)/2  # median x, becomes _x in blob, replaces ix and lx?
    dx = x - _x  # full comp(x) and comp(S) are conditional, internal vars are secondary
    Dx += dx  # for blob norm, orient eval, by OG vs. Mx += mx, += |dx| for curved max_L

    L2 += len(e_)  # e_ in P is buffered in Py_, no separate e2_
    I2 += I
    D2 += D; Dy2 += Dy
    M2 += M; My2 += My
    G2 += G  # blob orient value?
    OG += oG  # vertical contiguity for comp_P eval?
    Olp += olp  # adds to blob orient and comp_P cost?

    Py_.append((s, ix, lx, I, D, Dy, M, My, G, oG, olp, e_, Dx))  # Dx to normalize P before comp_P

    blob = s, x, ix, lx, Dx, (L2, I2, D2, Dy2, M2, My2, G2, OG, Olp), Py_
    # S_par tuple in scan_Py_, incr_PP, orient?
    return blob


def term_blob(typ, blob):  # eval for orient(), incr_comp(), scan_Py_(), before full loading?

    s, x, ix, lx, Dx, max_L, (L2, I2, D2, Dy2, M2, My2, G2, OG, Olp), Py_ = blob
    rdn = Olp / L2  # rdn per blob, alt Ps (if not alt blobs) are complete?
    norm = 0

    if G2 * Dx > ave * 9 * rdn and len(Py_) > 2:  # if > ave * nvars: eval for hypot compute?
       blob, norm = orient(blob)  # orient for comp_P and comp_blob

    if G2 > ave * 99 * rdn and len(Py_) > 2:  # comp_P cost, or if len(Py_) > n+1: for fuzzy comp

       blob = scan_Py_(typ, blob, norm)  # blob norm -> P norm, no eval per P
       # S_ders += norm_ders, PM,PD, incr_comp -> deeper P if G2 += PM | PD?:

    if G2 > ave * 99 * rdn and len(Py_) > 2:  # original | oriented blob eval for internal incr_comp:
        e_, e__ = [],[]  # 2D array of ps | ds is extracted from Py_, also adjacent Py_s?

        for P in Py_:
            for e in P[11]:  # e: (p, d, dy, m, my), g, alt_g
                if typ:
                    e_.append(e[0]); r = rng+1  # e = p
                else:
                    e_.append(e[1]); r = rng  # e = d

            e__.append((e_, P[3]))  # last x = P[3]: local vs. global X?

        blob = frame(e__, r)  # separate X and Y, or lighter incr_comp(blob)?

    return blob, rdn

def orient(blob):  # orientation: rescan and P norm, per blob | blob_net | PP | PP_net

    s, x, ix, lx, Dx, max_L, (L2, I2, D2, Dy2, M2, My2, G2, OG, Olp), Py_ = blob
    # no typ, norm, rdn?

    ver_L = math.hypot(Dx, len(Py_))  # slanted vertical dimension
    mlt = ver_L / len(Py_)  # ver_L multiplier = lat_L divider
    lat_L = max_L / mlt  # orthogonal projection of max_lat_L in Py_

    if lat_L - ave * 99 > ver_L:  # ave dL per M_yP_- M_Py_ > cost of scan_e__, form_yP_) y_blob_, scan_yP_:

        e__ = []
        for P in Py_:
            e__.append((P[9], P[2]))  # e_, last x
        e__ = e__.sort(key=lambda e_: e_[1], reverse=True)  # sort by last x

        ''' e__: 2D array of tuples per pixel, extracted for blob sort and rescan:
        vertical-first, possibly by diagonal x ^ y, or by n-pixels angle nx ^ ny, 
        if G2 * ((Dx - near alt dx) ^ (Dy - near alt dy))? '''

        e_, _x = e__.pop
        y, olp, ovG, odG = 0,0,0,0  # vertical ydP x yvP overlap
        yP_, dP, dP_, _dP_, dblob_, vP, vP_, _vP_, vblob_ = [],[],[],[],[],[],[],[],[]  # deeper def later

        for e in e_:  # _e_ initialization per blob by form_Ps with empty d_grp, v_grp, olp, no scan_P_:

            y += 1; (p, d, dy, m, my), dg, vg = e  # no t2 norm by axis-scan deviation: cost > accuracy gain?
            t2 = p, dy, d, my, m  # orthogonal reorder for form_P:

            olp, ovG, odG, vP, dP, vP_, _vP_, vblob_ = form_P(1, t2, vg, dg, olp, ovG, odG, vP, dP, vP_, _vP_, vblob_, y)
            olp, odG, ovG, dP, vP, dP_, _dP_, dblob_ = form_P(0, t2, dg, vg, olp, odG, ovG, dP, vP, dP_, _dP_, dblob_, y)

            yP_.append((dP, dP_, _dP_, dblob_, vP, vP_, _vP_, vblob_, olp, ovG, odG))

        for e_, x in e__:

            new_yP_ = []  # init per y-line of an input blob
            y = 0; dx = x - _x
            if dx: e_.pop(dx)  # align e, _e: shift or rotate by dx pops? or popleft if iterator:
            else: yP_.pop(dx)

            for e, (dP, dP_, _dP_, dblob_, vP, vP_, _vP_, vblob_, olp, ovG, odG) in zip(e_, yP_):

                y += 1; (p, d, dy, m, my), dg, vg = e
                t2 = p, dy, d, my, m  # vertical dimension first

                olp, ovG, odG, vP, dP, vP_, _vP_, vblob_ = form_P(1, t2, vg, dg, olp, ovG, odG, vP, dP, vP_, _vP_, vblob_, y)
                olp, odG, ovG, dP, vP, dP_, _dP_, dblob_ = form_P(0, t2, dg, vg, olp, odG, ovG, dP, vP, dP_, _dP_, dblob_, y)

                new_yP_.append((dP, dP_, _dP_, dblob_, vP, vP_, _vP_, vblob_, olp, ovG, odG))

            yP_ = new_yP_, x  # Ps are yPs, form_P calls underloaded yblob = scan_P_ or scan_yP_: less fork eval?
            # no change in G, only ind ders and future M_ders?

    if mlt * G2 > ave * 99:  # gain - cost of normalizing P ders by Dx angle, for original or rescanned blob

       norm = 1  # G2 + M|D after comp_P
       rL = ver_L / lat_L  # both scaled by rotation per Dx, ders adjusted for comp_P and comp_blob:

       blob[6][2] = (D2 * rL + Dy2 / rL) / 2 / mlt  # est D2 over ver_L, Ders sum in ver / lat ratio
       blob[6][3] = (Dy2 / rL - D2 * rL) / 2 * mlt  # est Dy2 over lat_L,
       blob[6][4] = (M2 * rL + My2 / rL) / 2 / mlt  # est M2 over ver_L
       blob[6][5] = (My2 / rL + M2 * rL) / 2 * mlt  # est My2 over lat_L; G is combined: not adjusted

    else: norm = 0
    return blob, norm

''' diagonal blob (+ adjacent blobs) rescan and redef by normalized quad, if gain > cost?:

    d = (d + dy) / 2 / 1.4  # est d over ver_L, ders sum in 1/1 ver / lat ratio
    dy = (dy - d) / 2 * 1.4  # est dy over lat_L,
    m = (m + my) / 2 / 1.4  # est m over ver_L
    my = (my + m) / 2 * 1.4  # est my over lat_L
             
    then blob scan across max Dx ^ Dy axis?  g is combined, orient-neutral?
    or P redef by ortho_dx / ave_x scan line: overlap | stretch at alt ends? 
    or analog re-input for axis-aligned quads: more accurate than norm for P der comp, blob redef? 
'''

def scan_Py_(typ, blob, norm):  # scan of vertical Py_ -> comp_P -> 2D value PPs and difference PPs

    vPP = 0,[],[]  # s, PP (with S_ders), Py_ (with P_ders and e_ per P in Py)
    dPP = 0,[],[]  # PP: L2, I2, D2, Dy2, M2, My2, G2, Olp2

    SvPP, SdPP, Sv_, Sd_ = [],[],[],[]
    vPP_, dPP_, yP_ = [],[],[]

    Py_ = blob[2]  # unless oriented?
    _P = Py_.popleft()  # initial comparand

    while Py_:  # comp_P starts from 2nd P, top-down

        P = Py_.popleft()
        _P, _vs, _ds = comp_P(typ, P, _P, norm)  # per blob, before orient

        while Py_:  # form_PP starts from 3rd P

            P = Py_.popleft()
            P, vs, ds = comp_P(typ, P, _P, norm)  # P: S_vars += S_ders in comp_P

            if vs == _vs:
                vPP = incr_PP(1, P, vPP)
            else:
                vPP = term_PP(1, vPP)  # SPP += S, PP eval for orient, incr_comp_P, scan_par..?
                vPP_.append(vPP)
                for par, S in zip(vPP[1], SvPP):  # blob-wide summation of 16 S_vars from incr_PP
                    S += par
                    Sv_.append(S)  # or S is directly modified in SvPP?
                SvPP = Sv_  # but SPP is redundant, if len(PP_) > ave?
                vPP = vs, [], []  # s, PP, Py_ init

            if ds == _ds:
                dPP = incr_PP(0, P, dPP)
            else:
                dPP = term_PP(0, dPP)
                dPP_.append(dPP)
                for var, S in zip(dPP[1], SdPP):
                    S += var
                    Sd_.append(S)
                SdPP = Sd_
                dPP = ds,[],[]

            _P = P; _vs = vs; _ds = ds

    ''' S_ders | S_vars eval for PP ) blob ) network orient, incr distance | derivation comp_P
        redun alt P ) pP) PP ) blob ) network? '''

    return blob, SvPP, vPP_, SdPP, dPP_  # blob | PP_? comp_P over fork_, after comp_segment?


def comp_P(typ, P, _P, norm):  # forms vertical derivatives of P vars, also conditional ders from DIV comp

    s, ix, x, I, D, Dy, M, My, G, oG, Olp, e_, Dx = P
    _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _oG, _Olp, _e_, _Dx = _P

    ddx = 0  # optional, 2Le norm / D? s_ddx and s_dL correlate, s_dx position and s_dL dimension don't?

    ix = x - len(e_)  # initial and last coordinates of P
    dx = x - len(e_)/2 - _x - len(_e_)/2  # Dx? comp(dx), ddx = Ddx / h?

    mx = x - _ix  # vx = ave_dx - dx: distance (cost) decrease vs. benefit incr? or:
    if ix > _ix: mx -= ix - _ix  # mx = x olp, - a_mx -> vxP, distant P mx = -(a_dx - dx)?

    dL = len(e_) - len(_e_); mL = min(len(e_), len(_e_))  # relative olp = mx / L? ext_miss: Ddx + DL?
    dI = I - _I; mI = min(I, _I)  # L and I are dims vs. ders, not rdn | select, I per quad, no norm?

    if norm:  # derivatives are Dx-normalized before comp:
        hyp = math.hypot(Dx, 1)  # len incr = hyp / 1 (vert distance=1)

        D = (D * hyp + Dy / hyp) / 2 / hyp  # est D over ver_L, Ders summed in ver / lat ratio
        Dy= (Dy / hyp - D * hyp) / 2 * hyp  # est D over lat_L
        M = (M * hyp + My / hyp) / 2 / hyp  # est M over ver_L
        My= (My / hyp + M * hyp) / 2 * hyp  # est M over lat_L; G is combined: not adjusted

    dD = D - _D; mD = min(D, _D)
    dM = M - _M; mM = min(M, _M)

    dDy = Dy - _Dy; mDy = min(Dy, _Dy)  # lat sum of y_ders also indicates P match and orientation?
    dMy = My - _My; mMy = min(My, _My)

    # oG in Pm | Pd: lat + vert- quantified e_ overlap (mx)?  no G comp: redundant to ders

    Pd = ddx + dL + dI + dD + dDy + dM + dMy  # defines dPP, dx does not correlate
    Pm = mx + mL + mI + mD + mDy + mM + mMy  # defines vPP; comb rep value = Pm * 2 + Pd?

    if dI * dL > div_a:  # potential d compression, vs. ave * 21(7*3)?

        # DIV comp: cross-scale d, neg if cross-sign, no ndx: single, yes nmx: summed?
        # for S: summed vars I, D, M: nS = S * rL, ~ rS,rP: L defines P?

        rL = len(e_) / len(_e_)  # L defines P, SUB comp of rL-normalized nS:
        nI = I * rL; ndI = nI - _I; nmI = min(nI, _I)  # vs. nI = dI * nrL?

        nD = D * rL; ndD = nD - _D; nmD = min(nD, _D)
        nM = M * rL; ndM = nM - _M; nmM = min(nM, _M)

        nDy = Dy * rL; ndDy = nDy - _Dy; nmDy = min(nDy, _Dy)
        nMy = My * rL; ndMy = nMy - _My; nmMy = min(nMy, _My)

        Pnm = mx + nmI + nmD + nmDy + nmM + nmMy  # normalized m defines norm_vPP, if rL

        if Pm > Pnm: nvPP_rdn = 1; vPP_rdn = 0  # added to rdn, or diff alt, olp, div rdn?
        else: vPP_rdn = 1; nvPP_rdn = 0

        Pnd = ddx + ndI + ndD + ndDy + ndM + ndMy  # normalized d defines norm_dPP or ndPP

        if Pd > Pnd: ndPP_rdn = 1; dPP_rdn = 0  # value = D | nD
        else: dPP_rdn = 1; ndPP_rdn = 0

        div_f = 1
        nvars = Pnm, nmI, nmD, nmDy, nmM, nmMy, vPP_rdn, nvPP_rdn, \
                Pnd, ndI, ndD, ndDy, ndM, nmMy, dPP_rdn, ndPP_rdn

    else:
        div_f = 0  # DIV comp flag
        nvars = 0  # DIV + norm derivatives

    P_ders = Pm, Pd, mx, dx, mL, dL, mI, dI, mD, dD, mDy, dDy, mM, dM, mMy, dMy, div_f, nvars

    vs = 1 if Pm > ave * 7 > 0 else 0  # comp cost = ave * 7, or rep cost: n vars per P?
    ds = 1 if Pd > 0 else 0

    return (P, P_ders), vs, ds


''' no comp_e_(e_, _e_, yP_): vert comp by ycomp, ortho P by orientation?
    comp_P is not fuzzy: x, y vars are already fuzzy?
    
    no DIV comp(L): match is insignificant and redundant to mS, mLPs and dLPs only?:

    if dL: nL = len(e_) // len(_e_)  # L match = min L mult
    else: nL = len(_e_) // len(e_)
    fL = len(e_) % len(_e_)  # miss = remainder 

    no comp aS: m_aS * rL cost, minor cpr / nL? no DIV S: weak nS = S // _S; fS = rS - nS  
    or aS if positive eV (not eD?) = mx + mL -ave:

    aI = I / L; dI = aI - _aI; mI = min(aI, _aI)  
    aD = D / L; dD = aD - _aD; mD = min(aD, _aD)  
    aM = M / L; dM = aM - _aM; mM = min(aM, _aM)

    d_aS comp if cs D_aS, iter dS - S -> (n, M, diff): var precision or modulo + remainder? 
    pP_ eval in +vPPs only, per rdn = alt_rdn * fork_rdn * norm_rdn, then cost of adjust for pP_rdn? '''


def incr_PP(typ, P, PP):  # increments continued vPPs or dPPs (not pPs): incr_blob + P_ders?

    P, P_ders, S_ders = P
    s, ix, x, I, D, Dy, M, My, G, oG, Olp, e_ = P
    L2, I2, D2, Dy2, M2, My2, G2, OG, Olp2, Py_ = PP

    L2 += len(e_)
    I2 += I
    D2 += D; Dy2 += Dy
    M2 += M; My2 += My
    G2 += G
    OG += oG
    Olp2 += Olp
    Py_.appendleft((P, P_ders))

    Pm, Pd, mx, dx, mL, dL, mI, dI, mD, dD, mDy, dDy, mM, dM, mMy, dMy, div_f, nvars = P_ders
    _dx, Ddx, \
    PM, PD, Mx, Dx, ML, DL, MI, DI, MD, DD, MDy, DDy, MM, DM, MMy, DMy, div_f, nVars = S_ders

    ddx = dx - _dx  # no ddxP_ or mdx: olp of dxPs?
    Ddx += abs(ddx)  # PP value of P norm | orient per indiv dx: m (ddx, dL, dS)?

    # summed per PP, then per blob for form_pP_ or orient eval?

    PM += Pm; PD += Pd  # replace by zip (S_ders, P_ders)
    Mx += mx; Dx += dx; ML += mL; DL += dL; ML += mI; DL += dI
    MD += mD; DD += dD; MDy += mDy; DDy += dDy; MM += mM; DM += dM; MMy += mMy; DMy += dMy

    S_inps = s, L2, I2, D2, Dy2, M2, My2, G2, Olp2, Py_
    S_ders = PM, PD, Mx, Dx, ML, DL, MI, DI, MD, DD, MDy, DDy, MM, DM, MMy, DMy

    return S_inps, S_ders


def term_PP(typ, PP):  # eval for orient as term_blob, + incr_comp_P, scan_par_:

    (s, L2, I2, D2, Dy2, M2, My2, G2, Olp2, Py_), \
    (PM, PD, Mx, Dx, ML, DL, MI, DI, MD, DD, MDy, DDy, MM, DM, MMy, DMy) = PP

    rdn = Olp2 / L2  # rdn per PP, alt Ps (if not alt PPs) are complete?

    if G2 * Dx > ave * 9 * rdn and len(Py_) > 2:
       PP = orient(typ, rdn, PP) # PP norm or rescan: relative to and within parent blob

    # for incr_comp(oriented PP), comp_PP(oriented PP, blob), and extended comp_P:

    if G2 + PM > ave * 99 * rdn and len(Py_) > 2:
       PP = incr_range_comp_P(typ, PP)  # forming incrementally fuzzy PP

    if G2 + PD > ave * 99 * rdn and len(Py_) > 2:
       PP = incr_deriv_comp_P(typ, PP)  # forming incrementally higher-derivation PP

    if G2 + PM > ave * 99 * rdn and len(Py_) > 2:
       PP = scan_parameters(0, PP)  # forming vpP_ and S_p_ders

    if G2 + PD > ave * 99 * rdn and len(Py_) > 2:
       PP = scan_parameters(1, PP)  # forming dpP_ and S_p_ders

    return PP

''' incr_comp() ~ recursive_comp() in line_POC(), with Ps instead of pixels?
    with rescan: recursion per p | d (signed): frame(meta_blob | blob | PP)? '''

def incr_range_comp_P(typ, PP):
    return PP

def incr_deriv_comp_P(typ, PP):
    return PP

def scan_parameters(typ, PP):  # at term_network, term_blob, or term_PP: + P_ders and nvars?

    parameters = PP
    for (P, S_ders) in parameters:

        for (S, Mp, Dp, p_) in S_ders:  # form_pP select per S_der, includes all P_ders and nvars?

            if Mp > ave * 9 * 5 * 2:  # Mp > ave PP * ave pP rdn * rdn to PP
                vpP_ = []
                M_vpP, D_vpP, vpP_ = form_pP_(0, p_, P[1], vpP_)  # P[1] = P_ders

                # MpP eval for scan_pP_, comp_pP, or after orient: not affected?

            if Dp > ave * 9 * 5 * 4:  # half rep value?
                dpP_ = []
                M_dpP, D_dpP, dpP_ = form_pP_(1, p_, P[1], dpP_)  # P[1] = P_ders

    return PP

def form_pP_(typ, par_, P_ders, pP_):  # forming parameter patterns within PP, for each parameter

    # form_pP eval by PP' |Vp| or |Dp|: + ave rdn = 5 (2.5 * 2), or summed rdn for !max ps?

    vpP_, dpP_ = [],[]
    vpP = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, []
    dpP = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, []
    MpP, DpP = 0, 0

    (p, mp, dp) = par_.pop()  # no tSp, tMp, tDp
    S = p, Mp = mp, Dp = dp, p_ = []  # core pP init, or full pP: = PP?

    _vps = 1 if mp > ave * 7 > 0 else 0  # comp cost = ave * 7, or rep cost: n vars per P?
    _dps = 1 if dp > 0 else 0

    for (p, mp, dp) in par_:  # all vars are summed in incr_pP

        vps = 1 if mp > ave * 7 > 0 else 0  # comp cost = ave * 7, or rep cost: n vars per P?
        dps = 1 if dp > 0 else 0

        if vps == _vps:
            vpP += p  # unfolded incr_pP(typ, p, P_ders, vpP)?
        else:
            term_pP(typ, vpP)
            vpP_.append(vpP)  # comp_pP eval in scan_par_?
            vpP = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, []
            MpP += abs(vpP[1])

        # same for dpP_: generic form_pP?

        _p = p; _vps = vps; _dps = dps

    return MpP, DpP, pP_

    # LIDV per dx, L, I, D, M? also alt2_: fork_ alt_ concat, for rdn per PP?
    # fpP fb to define vpPs: a_mx = 2; a_mw = 2; a_mI = 256; a_mD = 128; a_mM = 128


def term_pP(typ, pP):  # from form_pP, eval for re_comp? or folded?
    return pP

def scan_pP_(typ, pP_):  # pP rdn per vertical overlap? simple, folded in scan_par_?
    return pP_

def comp_pP(pP, _pP):  # with/out orient, from scan_pP_
    return pP

def scan_PP_(PP_):  # within a blob, also within blob_: network?
    return PP_

def comp_PP(PP, _PP):  # compares PPs within a blob | network, -> forking PPP_: very rare?
    return PP

def scan_blob_(blob_):  # after full blob network termination,
    return blob_

def comp_blob(blob, _blob):  # compares blob segments
    return blob


''' np.array for direct accumulation, vs. iterator of initialization:
    P2_ = np.array([blob, vPP, dPP],
    dtype = [('crit', 'i4'), ('rdn', 'i4'), ('W', 'i4'), ('I2', 'i4'), ('D2', 'i4'), ('Dy2', 'i4'),
    ('M2', 'i4'), ('My2', 'i4'), ('G2', 'i4'), ('rdn2', 'i4'), ('alt2_', list), ('Py_', list)]) 
'''

def frame(f, r):  # postfix '_' denotes array vs. element, prefix '_' denotes higher-line variable

    global ave; ave = 127  # filters, ultimately set by separate feedback, then ave *= rng?
    global rng; rng = r  # r is passed as feedback or incremented in term_blob

    global div_a; div_a = 127  # not justified
    global ave_k; ave_k = 0.25  # average V / I initialization

    global Y; global X; Y, X = f.shape  # Y: frame height, X: frame width
    global y; y = 0

    _vP_, _dP_, frame_ = [], [], []

    t2_ = deque(maxlen=rng)  # vertical buffer of incomplete pixel tuples, for fuzzy ycomp
    t2__ = []  # vertical buffer + horizontal line: 2D array of 2D tuples, deque for speed?
    p_ = f[0, :]  # first line of pixels
    t_ = comp(p_)  # after part_comp (pop, no t_.append) while x < rng?

    for t in t_:
        p, d, m = t
        t2 = p, d, 0, m, 0  # fdy and fmy initialized at 0
        t2_.append(t2)  # only one tuple per first-line t2_
        t2__.append(t2_)  # in same order as t_

    # part_ycomp (pop, no form_P) while y < rng?

    for y in range(1, Y):  # or Y-1: default term_blob in scan_P_ at y = Y?

        p_ = f[y, :]  # vertical coordinate y is index of new line p_
        t_ = comp(p_)  # lateral pixel comparison
        t2__, _vP_, _dP_, vg_blob_, dg_blob_ = ycomp(t_, t2__, _vP_, _dP_) # vertical pixel comp

        frame_.append((vg_blob_, dg_blob_))  # line of blobs is added to frame of blobs

    return frame_  # frame of 2D patterns is outputted to level 2

f = misc.face(gray=True)  # input frame of pixels
f = f.astype(int)
frame(f, 1)

