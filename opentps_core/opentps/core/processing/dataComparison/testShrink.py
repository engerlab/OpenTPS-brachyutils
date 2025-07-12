import numpy as np

def indexes(array1, array2):
    L1 = array1.tolist()
    L2 = array2.tolist()
    L_ind = []
    i = 0
    while i < len(L1):
        nbrOccurence = L1.count(L1[i])
        L_ind.append(L2[i:i+nbrOccurence])
        i += nbrOccurence
    return L_ind

def eval(M2, difference):
    index_dim1, index_dim2, index_dim3 = np.where(M2==1)
    print(index_dim1)

    ligne_sum = []
    count = 0
    ind_col = indexes(index_dim1, index_dim2)
    #ind_dim3 = indexes(index_dim1, index_dim3)
    #print("ind", indexes(index_dim1, index_dim2))
    i = 0
    for L in ind_col:
        for k in L:
            if difference[index_dim1[i], k, index_dim3[i]]==1:
                count += 1
        #print(count)
        ligne_sum.append(count)
        count = 0
        i += len(L)
    return ligne_sum