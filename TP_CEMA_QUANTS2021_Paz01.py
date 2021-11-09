# -*- coding: utf-8 -*-
"""
Created on Nov 2021

@author: Daniel Pablo Paz

Curso Finanzas QUANTS Cema 2021 - Trabajo Práctico Final

"""
################# FUNCIONES  #########################
## se agregan en el mismo archivo para mayor claridad explicativa del TP


import pandas as pd
import mplfinance 
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
import numpy as np
import requests
import json
import time
import datetime as st
from datetime import date
import datetime as dt

## Funciones para determinar niveles criticos de soportes y resistencias ticker

def isSupport(df,i):
  support = df['Low'][i] < df['Low'][i-1]  and df['Low'][i] < df['Low'][i+1] and df['Low'][i+1] < df['Low'][i+2] and df['Low'][i-1] < df['Low'][i-2]
  return support

def isResistance(df,i):
  resistance = df['High'][i] > df['High'][i-1]  and df['High'][i] > df['High'][i+1] and df['High'][i+1] > df['High'][i+2] and df['High'][i-1] > df['High'][i-2]
  return resistance

def minmax(df):
    
    minlist=pd.DataFrame()
    for i in range(2,df.shape[0]-2):
        
        if isSupport(df,i):
            minlist=minlist.append( {"Date": df["Date"][i], "Valor":df["Low"][i],"Tipo":"Min"},ignore_index=True)            
        elif isResistance(df,i):
            minlist=minlist.append(  {"Date": df["Date"][i], "Valor":df["Low"][i],"Tipo":"Max"}, ignore_index=True)
    minlist=minlist.set_index(["Date"])
    return minlist

def get_niveles_SR(df, zonas=100,lim=1):
    """
    Produce un listado de niveles de soportes y resistencias para el periodo analizado
    los niveles se definne como franjas difusas, agrupando zonas que concentran maximos o minimos
    Parameters
    ----------
    df : dataframe de precios de un ticker en formato OHLC
    zonas: divide el rango de precios para agrupar niveles, defecto=100
    Returns
    -------
    dataframe: index, date, valor, tipo(Soporte/Resistencia)
    """
    srdf=pd.DataFrame(columns=["Valor", "Tipo","Peso"])
    srdf=srdf.append( {"Valor":df["Low"].min(),"Tipo":"Soporte","Peso":1}, ignore_index=True)    
    srdf=srdf.append( {"Valor":df["High"].max(),"Tipo":"Resistencia","Peso":1}, ignore_index=True)
         
    for i in range(2,df.shape[0]-2):
        
        if isSupport(df,i):
            srdf=srdf.append( {"Valor":df["Low"][i],"Tipo":"Soporte","Peso":1}, ignore_index=True)            
        elif isResistance(df,i):
            srdf=srdf.append( {"Valor":df["High"][i],"Tipo":"Resistencia","Peso":1},ignore_index=True)
            
    if zonas < 100:
        niveles=srdf
        PrecioMax=df["High"].max()
        PrecioMin=df["Low"].min()
        zonas =np.linspace(PrecioMin,PrecioMax,num=zonas)
        niveles['Vzona'] = pd.cut(niveles.Valor, zonas)
        niveles_filtro=pd.DataFrame()
        niveles_filtro["Valor"]=niveles.Valor.groupby(niveles.Vzona).mean()
        niveles_filtro["Peso"]=niveles.Valor.groupby(niveles.Vzona).count()
        niveles_filtro["Tipo"]=niveles.Tipo.groupby(niveles.Vzona).first()
        niveles_filtro=niveles_filtro.loc[niveles_filtro.Peso>=lim]
        niveles_filtro=niveles_filtro.dropna()
        
        srdf=niveles_filtro
    
    srdf=srdf.sort_values(["Valor"])
    return srdf

### detecta los soportes y resistencias para el precio actual

def sr_actual(data):
    """
    Detecta las lineas de soporte y resistencia actuales
    y si se cruzo en forma asendente o descendentes desde el dia anterior
    
    """

    niv= get_niveles_SR(data)
    nlevels= int(niv["Valor"].shape[0])
    prec= data.ultimoPrecio[-1]
    prec_2= data.ultimoPrecio[-2]

    for level in range(0, nlevels-1):
        if niv.iloc[level]["Valor"] < prec and  niv.iloc[level]["Tipo"]=="Soporte" :
            nivelinf= niv.iloc[level]["Valor"]
                
        if niv.iloc[level]["Valor"] > prec and niv.iloc[level]["Tipo"]=="Resistencia" :
            nivelsup= niv.iloc[level]["Valor"]
            break
        
        else: nivelsup = niv.Valor.max()
    
    if  prec_2 > nivelsup:
        cruce=-1
    elif prec_2< nivelinf:
            cruce=1
    else: cruce= 0
    
    return prec, nivelinf,nivelsup, cruce


######## INDICADORES TECNICOS Bollinger y MACD
   
def bolingerBands(data, window_size=10, num_of_std=1.5):
    """
    Calcula bandas de Bollinger sobre un array de precios

    Parametros
    ----------
    stock_price : array
    window_size : periodo de calculo, default 20.
    num_of_std : ancho de las bandas en desvest, default 2

    Retorna
    -------
    Bbollinger_index: 100* (close - inf)/ (sup-inf)
    """
    stock_price = data.Close
    rolling_mean = stock_price.rolling(window=window_size).mean()
    rolling_std  = stock_price.rolling(window=window_size).std()
    upper_band = rolling_mean + (rolling_std*num_of_std)
    lower_band = rolling_mean - (rolling_std*num_of_std)
    data["PmedioLHCO"]=(data.High+data.Low+data.Open+data.Close)/4
    data["Bollinger_inf"]=lower_band
    data["Bollinger_sup"]=upper_band
    data["Bollinger_mean"]=rolling_mean
        
    bsup= data["Bollinger_sup"]
    binf= data["Bollinger_inf"]
        
    return binf,bsup

def macd(data, ema1=12, ema2=26):
    """
    Calcula MACD
    Retorna_ MACD, signal, macd (MACD100 0-100, relativo al maximo absoluto)
    """
    
    stock_price= data["Close"]    
    exp1=stock_price.ewm(span=ema1, adjust=False).mean()
    exp2=stock_price.ewm(span=ema2, adjust=False).mean()
    macd1=exp1-exp2
    exp3=macd1.ewm(span=9,adjust=False).mean()
    data["MACD"]=macd1
            
    return data["MACD"]

########## GRAFICADOr velas 

def graf_velas(data):
    """
    Construye un grafico de velas directamente desde matplotlib
    Input: grafico formato open.close.high.low
    """

    data["Vardia"] = abs(data["Open"] - data["Close"])
    data["Rango"] =data["High"]-data["Low"]
    data["Pmedio"]=(data["High"]+data["Low"]+data["Open"]+data["Close"])/4
    data["Base"] = np.where(data["Open"]<data["Close"] ,data["Open"],data["Close"])
    data["Color"]= np.where(data["Open"]<data["Close"] ,"Green","Red")
    bar_pos=data.Vardia.loc[data["Open"]<data["Close"]]
    bar_neg=data.Vardia.loc[data["Open"]>data["Close"]]
    
    plt.grid(color="lightgray",linestyle='-')
    plt.bar(data.index, data["Rango"], bottom=data["Low"],width=0.1,color="black" )
    plt.bar(data.index, data["Vardia"], bottom=data["Base"],width= 1,color=data.Color )
    plt.plot(data.index, data["Pmedio"],color="black", linestyle="--",linewidth=1)
        
    return data["Pmedio"]
    

###### ACCESO A LA API DE IOL

def leer_claves_txt(nombre_archivo):
    path1="" #ubicacion de archivo de claves iol
    txt= pd.read_csv(nombre_archivo)
    myuser=txt.iloc[0,0]
    mypass=txt.iloc[0,1]
    return myuser, mypass

### definir funciones

def hora():
    hora1=dt.datetime.now().strftime("%H:%M:%S")
    print(hora1)
    return hora


def pedir_token(myuser,mypass):
    url = "https://api.invertironline.com/token"
 
    data= {"username": myuser, "password": mypass, "grant_type":"password"}
    r= requests.post(url=url, data=data).json()
    token= r
    #print("Respuesta: ",r)
    return r

def actualizar_token(tk):
    
    exp=dt.datetime.strptime(tk[".expires"], "%a, %d %b %Y %H:%M:%S GMT")
    ahora= dt.datetime.utcnow()
    tiempo = exp-ahora
    dias=tiempo.days
    
    if dias==0:
        tokenOK= tk
        print ("token valido por:",tiempo)
    else:
        tokenOK= pedir_token(myuser,mypass)
        print("nuevo token")
        token=tokenok
        atoken=token["access_token"]
 
    return tokenOK

### acceso a la API de iol

def iol_getHist( ticker, desde,hasta,atoken,market="bCBA",compresion="d"):
    """ 
    Parametros
    ----------
    ticker , desde:fecha_ini, hasta:fecha_fin (mm-dd-yyyy) , compresion= "d" , "h"
    Retorna
    -------
    dataframe : Index(['ultimoPrecio', 'variacion', 'apertura', 'maximo', 'minimo',
       'fechaHora', 'tendencia', 'cierreAnterior', 'montoOperado',
       'volumenNominal', 'precioPromedio', 'moneda', 'precioAjuste',
       'interesesAbiertos', 'puntas', 'cantidadOperaciones'],
      dtype='object')
        
    """
   
    url_base= "https://api.invertironline.com/api/v2/"
    endpoint= "/Titulos/"+ticker+"/Cotizacion/seriehistorica/" 
    Tx_3= "/sinAjustar"
    url3= url_base +market+endpoint + desde +"/"+hasta + Tx_3
    headers={"Authorization":"Bearer " +atoken}
    datos_serie= requests.get(url=url3,headers=headers).json()
    print( ticker + " : Descargado a dataframe")
    
    data= pd.DataFrame(datos_serie)
    data.index=pd.to_datetime(data.fechaHora)
    data=data.resample(compresion).last()
    data["Low"]=data.minimo
    data["High"]=data.maximo
    data["Date"]=data.index
    data["Close"]=data.ultimoPrecio
    data["Open"]=data.apertura
    data["Volume"]=data.montoOperado
    data=data.drop(["moneda","interesesAbiertos","puntas"], axis=1)
    data=data.dropna()   
    return data




#%%  PROGRAMA PRINCIPAL

##### establecer time renge partiendo de HOY

t_inicio= dt.datetime.utcnow()

### leer usuario y password - generar 1er token
carpeta= "E:\my_git"
myuser, mypass= leer_claves_txt("E:\my_git/Daniel_Iol_kkklll.txt")

#txt= pd.read_csv("Daniel_Iol_kkklll.txt")
#myuser=txt.iloc[0,0]
#mypass=txt.iloc[0,1]

#### Inicializar el sistema

delta_dias= 180
hoy=date.today()
fecha_hoy =  hoy.isoformat()
ini = hoy - dt.timedelta(days=delta_dias)
ayer= hoy - dt.timedelta(days=1)
fecha_ini = ini.isoformat()
fecha_ayer = ayer.isoformat()

token=pedir_token(myuser,mypass)
token=actualizar_token(token)
atoken=token["access_token"]


tickers_scan = ['AAPL', 'MELI','AMZN','EBAY', 'TSLA','AMD','NVDA','INTC', 'CSCO',  
                'FB','TWTR','MSFT', 'GOOGL','ADBE', 'IBM', 'BP', 'NFLX', 'ORCL',
                'ITUB', 'VALE', 'PBR', 'GOLD','AUY', 'HSBC', 'KO','PEP', 'CAT', 'WMT',
                'XOM','VIST', 'PG','BA','GE','JNJ', 'MRK','GILD','ABT']

resumen= pd.DataFrame(columns=["ticker","p_1","p_2","soporte","resistencia","SR_cruce",
                               "MACD","Bollinger_inf", "Bollinger_sup","i_bollinger","i_resist"])
#### algoritmo principal
for ticker in tickers_scan:
    ##### obtener valores historicos
    data=iol_getHist( ticker, desde=fecha_ini,hasta=fecha_hoy,atoken=atoken,market="nyse")
    macd(data)
    binf,bsup= bolingerBands(data, window_size=10, num_of_std=1.5)
    niveles=get_niveles_SR(data,zonas=50)
    prec_1, soporte, resistencia , sr_cross= sr_actual(data)
    prec_2= prec_2=data.ultimoPrecio[-2]
    ultmacd=data.MACD[-1]
    b_inf=binf[-1]
    b_sup=bsup[-1]
    ##### calcula indices 
    i_bollinger= (prec_1-b_inf)/(b_sup-b_inf)  ### de -2 a +2 (estadisticamente 4 sigma)
    i_resist = (prec_1-soporte)/(resistencia-soporte)  ### de 0 a 1 entre soporte y resistencia
  
    resumen=resumen.append({"ticker":ticker,"p_1":prec_1,"p_2":prec_2,"soporte":soporte,
                        "resistencia": resistencia,"SR_cruce":sr_cross,"MACD":ultmacd,
                        "Bollinger_inf":b_inf, "Bollinger_sup":b_sup,
                        "i_bollinger":i_bollinger,"i_resist":i_resist}, ignore_index=True)
    ### Graficar 
    graf_velas(data)
    plt.title(ticker)
    plt.plot(data.index, data["Bollinger_mean"] , color="blue", linestyle="--",linewidth=3)
    plt.plot(data.index, data["Bollinger_sup"], color="blue", linestyle="--",linewidth=1)
    plt.plot(data.index,  data["Bollinger_inf"], color="blue", linestyle="--",linewidth=1)
    plt.legend(["Bollinger","B+","B-"])
    plt.xlabel("Fecha")
    plt.ylabel("Precio USD")
    plt.fill_between(data.index, data["Bollinger_inf"],data["Bollinger_sup"], color="#E6E6FA")
    nlevels= int(niveles["Valor"].shape[0])
    
    for level in range(0, nlevels):
        if niveles.iloc[level]["Tipo"]=='Soporte':
            plt.hlines(niveles.iloc[level]["Valor"],xmin=min(data['Date'])
                       ,xmax=max(data['Date']),colors='darkblue',linewidth=int(niveles.iloc[level]["Peso"]))
        else:
            plt.hlines(niveles.iloc[level]["Valor"],xmin=min(data['Date'])
                       ,xmax=max(data['Date']),colors='purple',linewidth=int(niveles.iloc[level]["Peso"]))
    plt.hlines(resistencia,xmin=min(data['Date']),xmax=max(data['Date']),colors='purple',linewidth=3)
    plt.hlines(prec_1,xmin=min(data['Date']),xmax=max(data['Date']),linestyles='dotted',colors='gray',linewidth=2)
    plt.hlines(soporte,xmin=min(data['Date']),xmax=max(data['Date']),colors='darkblue',linewidth=3)
    plt.show() 
    
    
### Informe de resultados comparativos
resumen.set_index("ticker")
print("Resumen guardado en excel", resumen)
nombre="indices_estrategia.xlsx"
resumen.to_excel(nombre)
  
### grafica comparacion de indices tickers, compra y venta recomendadas

plt.hlines(0.40,xmin=0,xmax=1,colors='darkblue',linewidth=1)
plt.vlines(0.50,ymin=0,ymax=1,colors='darkblue',linewidth=1)
plt.xlabel("Indice Bollinger")
plt.ylabel("Indice Soporte-Resistencia")
plt.annotate("Zona de Compra",xy=(0.2,0.1), color="blue",horizontalalignment='center')

for tik in range(resumen.shape[0]):
    
    colorxy="gray"
    if resumen.iloc[tik][5]==1: colorxy="green"
    if resumen.iloc[tik][5]==-1: colorxy="red"
       
    plt.scatter( resumen.iloc[tik][9], resumen.iloc[tik][10], color=colorxy)
    plt.annotate(resumen.iloc[tik][0], xy=(resumen.iloc[tik][9]+0.01, resumen.iloc[tik][10]))
      
plt.show()





  
### grafica comparacion de indices tickers, compra y venta recomendadas

plt.hlines(0.40,xmin=0,xmax=1,colors='darkblue',linewidth=1)
plt.vlines(0.50,ymin=0,ymax=1,colors='darkblue',linewidth=1)
plt.xlabel("Indice Bollinger")
plt.ylabel("Indice Soporte-Resistencia")
plt.annotate("Zona de Compra",xy=(0.2,0.1), color="blue",horizontalalignment='center')

for tik in range(resumen.shape[0]):
   
    colorxy="gray"
    if resumen.iloc[tik][5] == 1: colorxy="green"
    if resumen.iloc[tik][5] == -1: colorxy="red"
    
    plt.scatter( resumen.iloc[tik][9], resumen.iloc[tik][10], color=colorxy)
    plt.annotate(resumen.iloc[tik][0], xy=(resumen.iloc[tik][9]+0.01, resumen.iloc[tik][10]))
      
plt.show()



    
    
#%%