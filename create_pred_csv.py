# -*- coding: utf-8 -*-
"""create_pred-csv.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1zQgJOdixo-C1YGjwGbwe63s3c8KTtCHL
"""

import tensorflow as tf
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
import IPython
import IPython.display as ipd
from IPython.display import clear_output
import soundfile as sf
import numpy as np
import io
import pandas as pd
import time
from statistics import median, mean
from urllib.request import urlopen
import matplotlib.pyplot as plt
import scipy
from scipy.fftpack import fft,ifft
from scipy.io import wavfile # get the api
import wandb
from wandb.keras import WandbCallback

def play_audio_fragment(filename, start, end, samplerate = 50000):
    """Play a fragment of an audio file.
    Args:
        filename: path to the audio file
        start: start of the fragment in samples
        end: end of the fragment in samples
        samplerate: samplerate to use when reading the file"""
    if not filename.startswith("."):
        #filename = f"https://storage.googleapis.com/datathon2022/dataset1/{filename}.ogg"
        prefix = "./datathon2022\\datathon2022\\dataset1\\"
        filename = f"{prefix+filename}.wav"


    #if filename.startswith("http"):
        #filename = io.BytesIO(urlopen(filename).read())

    data, read_sr = sf.read(filename, start=start, stop=end)


    assert samplerate == read_sr, f"samplerate does not match {samplerate} (from file) != {read_sr} (function parameter)"

    IPython.display.display(IPython.display.Audio(data, rate=samplerate))
def export_audio_fragment(filename, start, end, iviend, samplerate = 50000):
    """Play a fragment of an audio file.
    Args:
        filename: path to the audio file
        start: start of the fragment in samples
        end: end of the fragment in samples
        samplerate: samplerate to use when reading the file"""
    if not filename.startswith("."):

        prefix = "./datathon2022\\datathon2022\\dataset1\\"
        filename = f"{prefix+filename}.wav"

    #data, read_sr = sf.read(filename, start=start, stop=end)
    data, read_sr = sf.read(filename)
    start =int(np.ceil(start*read_sr))
    end = int(np.ceil(iviend*read_sr))
    #print(len(data))
    #print(start,end)


    assert samplerate == read_sr, f"samplerate does not match {samplerate} (from file) != {read_sr} (function parameter)"
    data = data[start:end]
    #IPython.display.display(IPython.display.Audio(data, rate=samplerate))
    return data

def play_annotation_from_df(row, margin: int = 0, samplerate = 50000):
    """Play a fragment of a wav file in a jupyter notebook.
    Args:
        row: a row of a pandas dataframe with the following columns:
            - path: path to the wav file
            - offset: offset in seconds
            - duration: duration in seconds
        margin: margin in seconds to add to the start and end of the fragment
        samplerate: samplerate to use when reading the file
        """
    m = margin * samplerate # margin in samples
    start = max(int(np.floor(row['start'] - m)), 0)
    #end = int(np.ceil(row['start'] + row['duration'] * samplerate + m))
    end = row['end']
    filename = row['path']
    #print(row)
    #print(filename)
    play_audio_fragment(filename, start, end, samplerate)

def export_annotation_from_df(row, margin: int = 0, samplerate = 50000):
    """Play a fragment of a wav file in a jupyter notebook.
    Args:
        row: a row of a pandas dataframe with the following columns:
            - path: path to the wav file
            - offset: offset in seconds
            - duration: duration in seconds
        margin: margin in seconds to add to the start and end of the fragment
        samplerate: samplerate to use when reading the file
        """
    m = margin * samplerate # margin in samples
    start = max(int(np.floor(row['start'] - m)), 0)
    end = int(np.ceil(row['start'] + row['duration'] * samplerate + m))
    #end = int(np.ceil(row['end']))

    iviend = row['end']
    filename = row['path']

    return export_audio_fragment(filename, start, end, iviend, samplerate)

def export_noise(ruido, margin: int = 0, samplerate=50000):
    m = margin * samplerate # margin in samples
    start = max(int(np.floor(ruido.start - m)), 0)
    end = int(np.ceil(ruido.start + ruido.duration * samplerate + m))
    iviend = ruido.end
    filename = ruido.path
    return export_audio_fragment(filename, start, end, iviend, samplerate)


dataset2 = pd.read_csv("./datathon2022\\datathon2022\\dataset1\\labels_dataset1_v2.csv")

"""
noises es un archivo creado por nosotros luego de analizar manualmente los datos y encontrar momentos en los audios
donde solo se escucha ruido.
El objetivo de noises es crear una nueva clasificacion para distinguir ahora cuando un sonido es "nothing"
"""

noises = pd.read_csv("./datathon2022\\datathon2022\\dataset1\\noises.csv")
dataset2 = pd.concat([dataset2,noises], ignore_index = True)


def f(signal, fs_rate = 50000, xi=0,xf=20000,yi=0):
    """
    Esta funcion es para transformar la señal en forma de (amplitud(tiempo))
    a amplitud(frecuencia)

    Devuelve [freqs_side, FFT_side] -> en la primera componente están las frecuencias
    y en la segunda componente las amplitudes.
    """

    N = signal.shape[0]
    secs = N / float(fs_rate)
    Ts = 1.0/fs_rate # sampling interval in time
    t = np.arange(0, secs, Ts) # time vector as scipy arange field / numpy.ndarray
    FFT = abs(fft(signal))
    FFT_side = FFT[range(N//2)] # one side FFT range AMPLITUDES
    freqs = scipy.fftpack.fftfreq(signal.size, t[1]-t[0])
    freqs_side = freqs[range(N//2)] # one side frequency range FRECUENCIAS

    return [freqs_side,FFT_side]

def fgpu(signal,dataFFT):
    """
    Mismo que f para gpu
    """

    N = len(signal)
    secs = N / 50000.0
    Ts = 1.0/50000.0 # sampling interval in time
    t = np.arange(0, secs, Ts) # time vector as scipy arange field / numpy.ndarray

    FFT = abs(dataFFT)


    FFT_side = FFT[range(N//2)] # one side FFT range AMPLITUDES

    freqs = scipy.fftpack.fftfreq(signal.size, t[1]-t[0])

    freqs_side = freqs[range(N//2)] # one side frequency range FRECUENCIAS

    return [freqs_side,FFT_side]


def r(i):
    """
    Funcion auxiliar para obtener la señal del audio.
    """
    return export_annotation_from_df(dataset2.loc[i])
def m(i,ds):
    """
    Funcion auxiliar para obtener la señal del audio.
    input:
    """
    return export_annotation_from_df(ds.loc[i])


def dato(K):
    antes = time.time()
    R = {}
    size = 25000/5000
    s = 0
    e = {}
    for i in range(0,5001):

        for j in range(s,len(K[0])):
            if K[0][j]<i*size:

                if(i*size not in R):
                    R[i*size] = []
                R[i*size].append(K[1][j])
            else:
                s = j
                break
    for key,value in R.items():

        e[key] = median(value)
    print("demoro dato",time.time()-antes)
    return e


def indexator(freqs):
    size = len(freqs)
    jump = size//1000
    #print(size,jump)
    I = [100,1000,3000,5000,12000,25000]
    indexs = []
    k = 0
    for i in range(0,size,jump):
        if k == 0:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                continue
        if k == 1:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
        if k == 2:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
        if k == 3:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                continue
        if k == 4:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                break
    return indexs

def indexator_noise(freqs):
    size = len(freqs)
    jump = size//1000
    #print(size,jump)
    I = [100,1000,3000,5000,12000,25000]
    indexs = []
    k = 0
    for i in range(0,size,jump):
        if k == 0:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                continue
        if k == 1:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
        if k == 2:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
        if k == 3:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                continue
        if k == 4:
            if freqs[i] < I[k]:
                continue
            else:
                indexs.append(i)
                k+=1
                break
    return indexs


def dato3(K):
    freqs = K[0]
    vals = K[1]
    size = len(freqs)
    partitions = indexator(K[0])
    X = np.split(K[0],partitions)
    Y = np.split(K[1],partitions)
    return [X,Y]

def dato4(K):
    freqs = K[0]
    vals = K[1]
    neurons = 2508/6

    R = []
    PIVOT = 0
    a = 0
    sold=0
    beg = False

    jumps = [int(len(vals[s])/neurons) for s in range(0,6)]

    for i in range(0,2508):
        s = int(i//neurons)
        if s != sold:
            beg = True
            a = 0
        if (len(vals[s])<neurons):
            R.append(np.median(vals[s]))
            continue
        jump = jumps[s]
        if (jump == 0):
            R.append(np.median(vals[s][a:a+1]))
            a+=1
            beg = True
        else:
            if(beg):
                a = 0
                beg = False
            R.append(np.median(vals[s][a:a+jump]))
            a += jump
        sold = s
    return R

## BINARY SEARCH
def binary_search_index(arr, val, start, end):
    if end is None:
        end = len(arr)-1
    if start is None:
        start = 0
    if(arr[0] >= val):
        return 0;
    if(arr[len(arr)-1] <= val):
        return len(arr)-1
    while (start <= end):
        mid = int((end+start)/2)
        if (val >= arr[mid-1] and val <= arr[mid]):
            if (abs(val-arr[mid-1]) < abs(val-arr[mid])):
                return mid - 1
            else:
                return mid
        else:
            if (arr[mid]< val):
                start = mid +1
            else:
                end = mid - 1
    return -1

## FILTRO GENERICO

def filterF(RF, signalF, reduction_fun,*args):
    """
    Esta funcion implementa filtros genericos para ser aplicados a una señal en su forma de amplitud(frecuencia)
    RF = Rango de frecuencias
    signalF = [AMPLITUDES,FRECUENCIAS]
    reduction_fun = función que lleva la lógica de como aplicar el filtro
    """

    R = 6000
    E = 8600
    N = 1
    k = 10
    if(len(args) > 0):
        R = args[0]
    if(len(args) > 1):
        N = args[1]
    if(len(args) > 2):
        E = args[2]
    if(len(args) > 3):
        k = args[3]

    freq = signalF[0].copy()
    amplitude = signalF[1].copy()
    startFilter = RF[0]
    endFilter = RF[1]

    i_start = binary_search_index(freq, startFilter,0,len(freq))
    i_end = binary_search_index(freq, endFilter,0,len(freq))

    new_signal_amplitude = np.split(amplitude,[i_start,i_end])
    new_signal_freq = np.split(freq,[i_start,i_end])

    new_signal_amplitude[1] = reduction_fun(new_signal_freq[1],new_signal_amplitude[1],R,N,E,k)
    new_signal = [freq,np.concatenate(new_signal_amplitude)]

    return new_signal

### FUNCIONES DE FILTRO

def cancel(X,Y,*args):
    """
    Funcion cancel, funcion constante 0
    """
    for i in range(0,len(Y)):
        Y[i] = 0
    return Y

def bandFilterSide(X,Y,R,n,*args):
    """
    filtro de paso de banda superior
    desde 0 Hz hasta R, reduce la amplitud con mas o menos amplitud según "n"
    esto es para filtrar sonidos "graves"
    """
    Y2 = Y.copy()

    i = binary_search_index(X,R,0,len(X))


    for j in range(0,i):
        Y2[j] = Y2[j]*((X[j]/R)**n)
    return Y2



def bandFilter(X,Y,S,n,E,k,*args):
    """
    filtro de
    desde 0 Hz hasta R, reduce la amplitud con mas o menos amplitud según "n"
    esto es para filtrar sonidos "graves"
    """
    Y2 = Y.copy()

    mid = S+((E-S)/2)
    #print(mid)
    i0 = binary_search_index(X,S,0,len(X))
    imid = binary_search_index(X,mid,0,len(X))
    i1 = binary_search_index(X,E,0,len(X))

    #print(i0,imid,i1,n)

    mx1 = max(Y2[i0:imid])
    mx2 = max(Y2[imid:i1])

    for j in range(i0,imid):
        #Y2[j] = Y2[j]*((S/X[j])**N(Y2[j]))
        Y2[j] = Y2[j]*((S/X[j])**(n*(1+k*(Y2[j]/mx1))))
    for j in range(i1,imid):
        #Y2[j] = Y2[j]*((X[j]/E)**decayRate(,))
        Y2[j] = Y2[j]*((X[j]/E)**(n*(1+k*(Y2[j]/mx2))))

    return Y2

## LOAD RUIDO
import noisereduce as nr
class Ruido():
    def __init__(self, path, start, end):
        self.path = path
        self.start = start
        self.end = end
        self.duration = end-start
ruido = Ruido("1a6ade9060f77d67c56e96997036c339", 187,192)
noise = export_noise(ruido)

## FUNCIONES PARA PREPAPARAR EL SUBMIT

SUBMISSION = [
"01767f8a26ee7958bdaad80f50f21873", "054f58f830e7c5285e5bada36c345303", "0550ebc7b63bd2c0a51c25418808c2da", "0723d88169bd201eb739d701b025c3f1", "09c5959a2ea99f9b627043e2c345d2c7", "0c0ddb1c5f6eff2ed61ab5981a2ecc76", "0cbd68f3e3b271d875bb6b4e785bed04", "17902ac9b47c468445535d977435719b", "1c870cba07b1721ce83d0230ad29ac27", "1ecdc73d4ede5054bc266027ee85717d", "2250b5d9c2b6f6ddc5ec7dd7a245f960", "25d6437b32bb9bebdea60d0a2d804256", "279d5a65213cfcaba3cc20f1732b4e46", "27c0e1ba4e990dfa577ef929ca980dde", "29cd6f1b944dff2e9fbd030a38227e77", "2cb1ea5bd6a54e30cc1f3f4e2eb345ce","2dd9572b1b73cdeb22c8ef978fef116b", "2e9dc571f516a2cc9d9d0a55e77b2edb", "30f3144bd98625c9ceb96007b02f8d39", "350f50b5cfaab6db7e89e240b3dfa71b", "35daa1daee9e2c4ee6776b1e7ea30023", "3ab2c1e299a482e9e5639051f72e3666", "3b3d534ff9ecaa2d496384f395767de5", "40803725bd29a907eafc82a5e1cdc9d6", "51856fb8023427116b0f0280a2a6b3fa", "5314149fff2453dc0cf57782978fe9e8", "57df89f066013e817fde45e6cf85ad71", "57e2517e787cc132945f97e5624f592e", "5ea4440f4919807b232350b583df9a54", "5f366e2c54080751ad9a46c47ccd2835", "5f7f9862fe35358088ed897c7bb578e2", "64d2a1294e81aac4c5a8fb5e3c52036f","672221d252ed82960addd82a47c3ffa7", "6752c7af5e42cd18b502f70073cd3f27", "6a94304dc4991087c738411d3eb4a4a4", "6d43df22bc5a6b65430bce36d5f2d38d", "6f0a1e5376f090bf052f0185d9999cc7", "73efa2618164520c0ae43eb17c7e8aa0", "7691e7a5c0a87603f46f9fd8a922f9ae", "7cb2bd0726ed980f5eafdf2aaae4c6c6", "829766a94ce6cdf7eaab0304573ad72d", "86d9de70af5d902e8ed0cb2dd995e06e", "8d60622fdfae997048cd16d100774fa0", "8d8bc83a4dbbc66aa5f5913ea5aece01", "94f88e5ca0865496e73461fd6ad00d7b", "9653e66ba82c221bcebf1ae9af87a29f", "97769c3b5d949a9a2d21bbfc71278bc4", "98201564e695dd198e92bf1f1d227412","98f4029a330e7d4789b07a32b171b0a7", "9c06591c5fd08338dee65a876c954b06", "a338b5687352e577f741a9bdde1f4ddc", "ab3f0b439cd8ae0bf2d2085556387cdf", "b28b25611638b56ad3c57b1e8cf025bc", "b32980cab33f244299eeb2de68703953", "b6916f850a3625da9c263ee77b183bb2", "b7ef63086bef05d643b3dca386154996", "ba7a412feee5092fa4dc0483ecec7e06", "c553b6097deba92a34f95f27c257f0f9", "cab6299bbf433890f38126227c5e9408", "cb70f7e4770cde93b547be23b2ed25c3", "cea599fc01d1bce7cff6c12b5dd3fb28", "d11f5e776a688b322ffeab92798440c8", "d4c6ed2ec958c437589d72025ac68ce4", "dbc0921618293b53fa80a9b22765aa58","dd093c40a9728812d278c80b04bb3586", "dfff14bc5caed74866586a57127beee0", "ebb37608fbe73d072485d4b447e91cab", "eccdfcc9573b2593c992a9147276d866", "f43b3951846402de1814e6d6d60e627e", "fb510a8dd4cf66a8f1e255a6085ab5c3"
]

PATHS2 = ["22fdfcd960203e6e18ab68988d00f3e9","5a8e5cfdab183be547b06ec85d216acb","7facf9dc202a4f85b05284f5b76bbdee"]
duration = 2
def openAudio(filename):

    #prefix = "./datathon2022\\datathon2022\\dataset1\\"
    prefix = "./datathon2022\\datathon2022\\dataset1\\submission\\"
    filename = f"{prefix+filename}.wav"
    data, read_sr = sf.read(filename)
    return data

def partitionAudio(data, partitionSize, rate=50000):
    totalFrames = len(data)
    framesPerPartition = int(rate*partitionSize)
    partitions = int(len(data)//framesPerPartition)
    P = []
    for i in range(0,partitions):
        P.append(data[i*framesPerPartition:(i+1)*framesPerPartition])
    return P

def preprocessAudio(P):
    PP = []
    counter = 0
    for signal in P:

        reduced = f(nr.reduce_noise(y=signal, y_noise=noise,sr = 50000))
        filteredfreqSigNoise = filterF([0,24999], reduced, bandFilterSide,6000,1)
        f_s8 = filterF([0,24999],filteredfreqSigNoise , bandFilter,7900,10,8600,10)

        s = dato4(dato3(f_s8))
        xx = []
        for v in s:
            xx.append(v)
        mx = max(xx)
        arr = []
        for kk in xx:
            arr.append(kk/mx)
        PP.append(arr)
        counter+=1
    return PP

def modelPrediction(X,model):
    predict_y = model.predict(X)
    return predict_y


class Prediction():
    def __init__(self,path,start,end,label):
        self.path = path
        self.start = start
        self.end = end
        self.label = label

    def print(self):
        print(self.path, self.start, self.end, self.label)


def clasiffy(path,predicted,res = duration):
    clasificaciones = []
    predic = predicted.copy()
    for p in predic:
        p[3]*=1
    tt = np.argmax(predic,axis=1)
    paths = []
    starts = []
    ends = []
    labels = []
    for t in range(0,len(tt)):
        if tt[t] == 0:
            clasificaciones.append(Prediction(path,t*res,(t+1)*res,"allfreq"))
            paths.append(path)
            starts.append(t*res)
            ends.append((t+1)*res)
            labels.append("allfreq")
        elif tt[t] == 1:
            clasificaciones.append(Prediction(path,t*res,(t+1)*res,"cetaceans_allfreq"))
            paths.append(path)
            starts.append(t*res)
            ends.append((t+1)*res)
            labels.append("cetaceans_allfreq")
        elif tt[t] == 2:
            clasificaciones.append(Prediction(path,t*res,(t+1)*res,"click"))
            paths.append(path)
            starts.append(t*res)
            ends.append((t+1)*res)
            labels.append("click")
        elif tt[t] == 3:
            continue
        elif tt[t] == 4:
            clasificaciones.append(Prediction(path,t*res,(t+1)*res,"whistle"))
            paths.append(path)
            starts.append(t*res)
            ends.append((t+1)*res)
            labels.append("whistle")
    pred = pd.DataFrame({
        "path":paths,
        "start":starts,
        "end":ends,
        "label": labels
    })


    return pred

PREDICCIONES = []
from keras.models import load_model
model_for_prediction = load_model("ultimo6.h5")
counter = 0
for audio in SUBMISSION:
    print("Voy por el:",counter)
    oppened = openAudio(audio)
    partitions = partitionAudio(oppened,duration)
    processed = preprocessAudio(partitions)
    predicted = modelPrediction(processed,model_for_prediction)
    pred = clasiffy(audio,predicted)
    PREDICCIONES.append(pred)
    counter+=1

final2 = pd.concat(PREDICCIONES,ignore_index=True)
final2.to_csv('pred.csv', index=False)

