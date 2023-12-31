import numpy as np
import scipy
from scipy import optimize
import os


def secondM2SymmConeWeighted(b, B, sumNorm, secM, signal, backg):
    # define a least squares problem structure

    
    bXX = b['XX'][0,0]; bYY = b['YY'][0,0]; bZZ = b['ZZ'][0,0]; bXY = b['XY'][0,0]; bXZ = b['XZ'][0,0]; bYZ = b['YZ'][0,0]

    Ix = secM[0] * bXX + secM[1] * bYY + secM[2] * bZZ + secM[3] * bXY + secM[4] * bXZ + secM[5] * bYZ
    Ix[Ix<0] = 0

    # Normalize second moment info and multiply by photon number
    Ix  = Ix / sumNorm; Ix = signal * Ix

    # Compute Fisher Information Matrix
    FIM = calFIMSecondM(B, Ix, signal, backg)


    # construct the M matrix
    M = np.array([[secM[0], secM[3], secM[4]],
        [secM[3], secM[1], secM[5]],
        [secM[4], secM[5], secM[2]]],dtype='float64')
    D,V = np.linalg.eig(M)
    V_real = np.real(V)
    D_real = np.real(D)

    idx_max_D = np.argmax(D_real)

    # initialization via SVD
    x0SVD = np.zeros((4,1))

    # Initial value based the largest eigen value
    #------------------------------------------------------------
    x0SVD[0] = np.real(V[0, idx_max_D])
    x0SVD[1] = np.real(V[1, idx_max_D])
    x0SVD[2] = np.real(V[2, idx_max_D])
    x0SVD[3] = 1.5 * np.max(D_real[idx_max_D]) - .5

    # upper and lower constraints for estimated first moments
    bound = [(-1, 1), (-1, 1), (-1, 1), (0, 1)]

    cons = {'type':'ineq', 'fun': constraint}

    # interior-point optimization
    M1estresults = optimize.minimize(objective_fun, x0SVD, bounds = bound, constraints = cons, args = (FIM, np.matrix(secM),))
    # print(M1estresults)
    estM1 = M1estresults['x']
    # print(estM1)
    # print(np.linalg.norm(estM1[0:2]))

    return estM1



def calFIMSecondM(B, I, s, backg):
    FIM = np.zeros((6, 6))

    Baa = B['aa'][0,0]; Bbb = B['bb'][0,0]; Bcc = B['cc'][0,0]; Bdd = B['dd'][0,0]; Bee = B['ee'][0,0]; Bff = B['ff'][0,0]
    Bab = B['ab'][0,0]; Bac = B['ac'][0,0]; Bad = B['ad'][0,0]; Bae = B['ae'][0,0]; Baf = B['af'][0,0]
    Bbc = B['bc'][0,0]; Bbd = B['bd'][0,0]; Bbe = B['be'][0,0]; Bbf = B['bf'][0,0]
    Bcd = B['cd'][0,0]; Bce = B['ce'][0,0]; Bcf = B['cf'][0,0]
    Bde = B['de'][0,0]; Bdf = B['df'][0,0]
    Bef = B['ef'][0,0]


    FIM[0, 0] = 0.5 * (s**2) * (sum(sum((Baa) / (I + backg))))
    FIM[1, 1] = 0.5 * (s**2) * (sum(sum((Bbb) / (I + backg))))
    FIM[2, 2] = 0.5 * (s**2) * (sum(sum((Bcc) / (I + backg))))
    FIM[3, 3] = 0.5 * (s**2) * (sum(sum((Bdd) / (I + backg))))
    FIM[4, 4] = 0.5 * (s**2) * (sum(sum((Bee) / (I + backg))))
    FIM[5, 5] = 0.5 * (s**2) * (sum(sum((Bff) / (I + backg))))

    FIM[0, 1] = (s**2) * (sum(sum((Bab) / (I + backg))))
    FIM[0, 2] = (s**2) * (sum(sum((Bac) / (I + backg))))
    FIM[0, 3] = (s**2) * (sum(sum((Bad) / (I + backg))))
    FIM[0, 4] = (s**2) * (sum(sum((Bae) / (I + backg))))
    FIM[0, 5] = (s**2) * (sum(sum((Baf) / (I + backg))))

    FIM[1, 2] = (s**2) * (sum(sum((Bbc) / (I + backg))))
    FIM[1, 3] = (s**2) * (sum(sum((Bbd) / (I + backg))))
    FIM[1, 4] = (s**2) * (sum(sum((Bbe) / (I + backg))))
    FIM[1, 5] = (s**2) * (sum(sum((Bbf) / (I + backg))))

    FIM[2, 3] = (s**2) * (sum(sum((Bcd) / (I + backg))))
    FIM[2, 4] = (s**2) * (sum(sum((Bce) / (I + backg))))
    FIM[2, 5] = (s**2) * (sum(sum((Bcf) / (I + backg))))

    FIM[3, 4] = (s**2) * (sum(sum((Bde) / (I + backg))))
    FIM[3, 5] = (s**2) * (sum(sum((Bdf) / (I + backg))))

    FIM[4, 5] = (s**2) * (sum(sum((Bef) / (I + backg))))

    FIM = FIM + np.transpose(FIM)

    return FIM


def symmCone2SecM(z):
    z = np.reshape(z, (1, 4), order='F')
    muxx = z[:,3] * z[:,0]**2 + (1 - z[:,3]) / 3
    muyy = z[:,3] * z[:,1]**2 + (1 - z[:,3]) / 3
    muzz = z[:,3] * z[:,2]**2 + (1 - z[:,3]) / 3
    muxy = z[:,3] * z[:,0] * z[:,1]
    muxz = z[:,3] * z[:,0] * z[:,2]
    muyz = z[:,3] * z[:,1] * z[:,2]
    out = np.array([[muxx[0]], [muyy[0]], [muzz[0]], [muxy[0]], [muxz[0]], [muyz[0]]])
    return out


def objective_fun(z, FIM, secM):
    '''Objective function, test lambda objective function first'''
    sC2SM = symmCone2SecM(z); # print(np.shape(sC2SM))
    # print(np.shape((sC2SM.T - secM)))
    # print(np.shape(np.matmul(np.matmul((sC2SM.T - secM), FIM), (sC2SM - secM.T))))
    # print(np.matmul(np.matmul((sC2SM.T - secM), FIM), (sC2SM - secM.T)))
    return np.matmul(np.matmul((np.transpose(sC2SM) - secM), FIM), (sC2SM - np.transpose(secM)))[0,0]

def constraint(z):
    '''Constraint function'''
    return np.sum(z[0:3]**2, 0) - 1