########################################################################################################
# PROJECT : FLO | BG-NBD ve Gamma-Gamma Modeli ile CLTV Prediction (Müşteri Yaşam Boyu Değeri Tahmini )
########################################################################################################

# Customer Lifetime Value, bir müşterinin bir şirketle olan ilişkisi boyunca, bu şirkete kazandıracağı parasal değerdir.

# Zaman projeksiyonlu olasılıksal CLTV Tahmini, bir müşterinin bir şirkete sağlayacağı gelirin tahmin edilmesine yönelik bir analiz türüdür.
# Bu yöntem, müşterinin geçmiş davranışlarını ve satın alma alışkanlıklarını kullanarak, gelecekteki satın alma olasılıklarını tahmin etmeye çalışır.
# Şirketlerin müşterileriyle ilişkilerini yönetmelerine ve pazarlama stratejilerini desteklemelerine yardımcı olur.

# CLTV prediction = BG/NBD Modeli x Gamma-Gamma Modeli
# CLTV prediction = Expected Total Transaction x Expected Average Profit  (Beklenen satın alma sayısı x Beklenen ortalama kazanç(kar))

# CLTV değerini, her bir müşteri için tahmin ederiz. Olasılık dağılımlarını kullanarak, genel kitlemizin davranışlarını modelleriz ve bunları kişilerin özeline indirgeriz.

## BG/NBD Modeli:      Müşterinin beklenen satın alma sayısını tahmin etmek için kullanılır. (Expected Total Transaction)
## Gamma-Gamma Modeli: Bir müşterinin beklenen ortalama karını tahmin etmek için kullanılır. (Expected average profit)


# Recency:           Müşteri son satın alma tarihi- Müşteri ilk satın alma tarihi
# Frequency:         Toplam işlem sayısı (fatura sayısı)
# Monetory:          AVERAGE harcama tutarı
# Customer Age (T):  Analiz tarihi - Müşterinin ilk satın alma tarihi


#### PROJE ADIMLARI ####
# 1. İş Problemi (Business Problem)
# 2. Gerekli Kütüphane ve Fonksiyonlar
# 3. Veriyi Anlama (Data Understanding)
# 4. Verinin Hazırlanması (Data Preperation)
# 5. CLTV Veri Yapısının Oluşturulması (Metriklerin hazırlanması)
# 6. BG-NBD Modeli ile Expected Number of Transaction
# 7. Gamma-Gamma Modeli ile Expected Average Profit
# 8. BG-NBD ve Gamma-Gamma Modeli ile CLTV'nin Hesaplanması
# 9. CLTV'ye Göre Segmentlerin Oluşturulması
# 10.Çalışmanın fonksiyonlaştırılması






##################################################################################
# 1. İş Problemi (Business Problem)
##################################################################################

# Türkiye ayakkabı pazarının öncü firmalarından FLO, müşterilerini satın alma alışkanlıkları üzerinden segmentlere ayırmak ve bu segmentler özelinde stratejiler geliştirmek istiyor.
# Ayrıca aşağıda, 7. adımda "Project's Business Questions" bölümunde yer alan soruların cevaplanması bekleniyor.

# Yaklaşık 20.000 müşteriye ait bilgileri içeren veri seti, son alışverişlerini 2020-2021 yıllarında OmniChannel (hem online hem offline alışveriş) olarak yapan müşterilerin geçmiş alışveriş davranışlarından elde edilen bilgilerden oluşmaktadır.

# Değişkenler
# master_id                         : Eşsiz müşteri numarası
# order_channel                     : Alışveriş yapılan platforma ait hangi kanalın kullanıldığı (Android, ios, Desktop, Mobile, Offline)
# last_order_channel                : En son alışverişin yapıldığı kanal
# first_order_date                  : Müşterinin yaptığı ilk alışveriş tarihi
# last_order_date                   : Müşterinin yaptığı son alışveriş tarihi
# last_order_date_online            : Muşterinin online platformda yaptığı son alışveriş tarihi
# last_order_date_offline           : Muşterinin offline platformda yaptığı son alışveriş tarihi
# order_num_total_ever_online       : Müşterinin online platformda yaptığı toplam alışveriş sayısı
# order_num_total_ever_offline      : Müşterinin offline'da yaptığı toplam alışveriş sayısı
# customer_value_total_ever_offline : Müşterinin offline alışverişlerinde ödediği toplam ücret
# customer_value_total_ever_online  : Müşterinin online alışverişlerinde ödediği toplam ücret
# interested_in_categories_12       : Müşterinin son 12 ayda alışveriş yaptığı kategorilerin listesi






##############################################################
# 2. Gerekli Kütüphane ve Fonksiyonlar
##############################################################

# pip install lifetimes
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from lifetimes.plotting import plot_period_transactions

pd.set_option('display.max_columns', None)    # tüm sütunlar gelsin
pd.set_option("display.width", 500)           # tüm sütunlar "yanyana" gelsin
pd.set_option("display.precision", 4)         # float türündeki sayılarda virgül sonrasi 4 basamak olsun
from sklearn.preprocessing import MinMaxScaler


# Bu fonksiyon, belirli bir değişkenin aykırı değerler için alt ve üst sınırlarını hesaplar (şsik deger)
def outlier_thresholds(dataframe, variable):
    quartile1 = dataframe[variable].quantile(0.01)    # Veri setinin belirtilen değişkeninin alt% 1'lik çeyreğini (1. percentile) hesaplar.
    quartile3 = dataframe[variable].quantile(0.99)    # Veri setinin belirtilen değişkeninin üst% 99'luk çeyreğini (99. percentile) hesaplar.
    interquantile_range = quartile3 - quartile1       # Çeyrekler arası aralığı hesaplar.
    up_limit = quartile3 + 1.5 * interquantile_range  # Üst sınırları hesaplar.
    low_limit = quartile1 - 1.5 * interquantile_range # Alt sınırları hesaplar.
    return low_limit, up_limit                        # Hesaplanan alt ve üst sınırları döndürür.


# Bu fonksiyon, belirli bir değişkenin aykırı değerlerini belirlenen alt ve üst sınırlarla değiştirmek için kullanılır.
# Not: cltv hesaplanırken frequency değerleri integer olması gerekmektedir. Bu nedenle alt ve üst limitlerini round() ile yuvarlayınız.
def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = outlier_thresholds(dataframe, variable)                     # Belirli değişken için alt ve üst sınırları outlier_thresholds fonksiyonundan alır.
    dataframe.loc[(dataframe[variable] < low_limit), variable] = round(low_limit,0)   # Aykırı değerleri alt sınıra eşitlemek isteniyorsa, yorum satırı kaldırılarak bu satırın etkinleştirilmesi gerekir.
    dataframe.loc[(dataframe[variable] > up_limit), variable] = round(up_limit,0)     # Aykırı değerler üst sınıra eşitlenir.






##################################################################################
# 3. Veriyi Anlama (Data Understanding)
##################################################################################

# Read from CSV
df_ = pd.read_csv("/Users/gozdemadendere/Desktop/PycharmProjects/CRM_Analytics/FLO_project_CLTV_prediction/flo_data_20k.csv")
df = df_.copy()

################################################
# Exploratory Data Analysis Function : Displays basic characteristics of the DataFrame.

def check_df(dataframe, head=5):
    print("__________________________________________________________________ FIRST 5 ROWS __________________________________________________________________ ")
    print(dataframe.head(head))
    print("__________________________________________________________________  LAST 5 ROWS __________________________________________________________________ ")
    print(dataframe.tail(head))
    print("__________________________________________________________________  DATA SHAPE ___________________________________________________________________ ")
    print(dataframe.shape)
    print("_________________________________________________________________  GENERAL INFO __________________________________________________________________ ")
    print(dataframe.info())
    print("__________________________________________________________________  NULL VALUES __________________________________________________________________ ")
    print(dataframe.isnull().sum().sort_values(ascending=False))
    print("_______________________________________________________________  DUPLICATED VALUES _______________________________________________________________ ")
    print(dataframe.duplicated().sum())
    print("____________________________________________________________________ DESCRIBE ____________________________________________________________________ ")
    print(dataframe.describe([0, 0.05, 0.1, 0.25, 0.50, 0.95, 0.99, 1]).T)

# Use the function
check_df(df)

################################################







##############################################################
# 4. Verinin Hazırlanması (Data Preperation)
##############################################################

### 1) NaN değerler yok, olsaydı içeren satırları silerdik veya doldurabilirdik.
df.isnull().sum()

### 2) min alışveriş sayıları ve harcama tutarları >= 1 olmalı, öyle görünüyor
df.describe()

### 3) Tarih ifade eden değişkenlerin tipini date'e çevirelim
df.dtypes
df["first_order_date"] = pd.to_datetime(df["first_order_date"])
df["last_order_date"] = pd.to_datetime(df["last_order_date"])
df["last_order_date_online"] = pd.to_datetime(df["last_order_date_online"])
df["last_order_date_offline"] = pd.to_datetime(df["last_order_date_offline"])


### 4) Omnichannel, müşterilerin hem online hem offline platformlardan alışveriş yaptığını ifade etmektedir.
# Her bir müşterinin toplam alışveriş sayısı ve harcaması için yeni değişkenler oluşturun.

df["total_order_number"] = df["order_num_total_ever_online"] + df["order_num_total_ever_offline"]
df["total_customer_value"] = df["customer_value_total_ever_online"] + df["customer_value_total_ever_offline"]

# master_id sutun ismini customer_id olarak degistirelim
df = df.rename(columns={"master_id": "customer_id"})

### 5) "order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline", "customer_value_total_ever_online" değişkenlerinin aykırı değerleri varsa baskılayanız.

# Yukarida hazirladigimiz fonksiyonlari kullanalim:
# Bu fonksiyon, belirli bir değişkenin aykırı değerlerini belirlenen alt ve üst sınırlarla değiştirmek için kullanılır.
replace_with_thresholds(df, "order_num_total_ever_online")
replace_with_thresholds(df, "order_num_total_ever_offline")
replace_with_thresholds(df, "customer_value_total_ever_offline")
replace_with_thresholds(df, "customer_value_total_ever_online")

df.describe()






###############################################################
# 5. CLTV Veri Yapısının Oluşturulması (Metriklerin hazırlanması)
###############################################################

# Recency:           Müşteri son satın alma tarihi- Müşteri ilk satın alma tarihi
# Frequency:         Toplam işlem sayısı (fatura sayısı)
# Monetory:          AVERAGE harcama tutarı
# Customer Age (T):  Analiz tarihi - Müşterinin ilk satın alma tarihi

### 1) Analizin yapıldığı günü tanımlayalım.  Dataframe deki en son satın alma tarihi 30 Mayıs 2021 ise:
df["last_order_date"].max()    # dataframe deki en son satın alma tarihi
today_date = dt.datetime(2021, 6, 1)

#######################################
# Note!! : Örnek olarak, cltv_prediction dosyasındaki projede, müşteri Customer id ler satırlarda çokladığı için, group by a aldırma işlemi yapmıştık.
# 4 metrik sütununu da (recency, frequency, T, monetary) lambda fonksiyonu ile hesaplatmıştık.
# Ayrıca o projede, invoice lar (first ve last ınvoicelar da) tek sütun içindeydi, bakılabilir.
#######################################


### 2) customer_id, recency_cltv_weekly, T_weekly, frequency ve monetary_cltv_avg değerlerinin yer aldığı yeni bir cltv dataframe oluşturunuz.
# Bu projede, orijinal dataframe de zaten her satırda eşsiz Customer id var. Yani Customer id ye göre group by yapmaya gerek yok.

# Önce orijinal df ye recency, frequency, monetary, T sütunlarini ekletelim.
df["recency"] = (df["last_order_date"] - df["first_order_date"]).dt.days
df["frequency"] = df["total_order_number"]
df["monetary"] = df["total_customer_value"] / df["total_order_number"]   # monetary: satın alma başına ortalama kazanç, total price i islem sayisina bolelim
df["T"] = (today_date - pd.to_datetime(df["first_order_date"])).dt.days

### 3) Recency ve Müşteri Yaşı (T) değerleri haftalık olmalı, haftalık cinse çevirelim: 7'ye bölerek
df["recency"] = df["recency"] / 7
df["T"] = df["T"] / 7


### 4) cltv_df isimli yeni bir dataframe olusturup ilgili 4 sutunu ekletelim
cltv_df = df.loc[:, ["customer_id", "recency", "frequency", "monetary", "T"]]

### 5) frequency >1 olmalidir !  df de min 2 gorunuyor, mantikli. >1 olmasaydi sunu demeliydik: cltv_df = cltv_df[(cltv_df['frequency'] > 1)]
cltv_df.describe().T

### 6) frequency integer olmalidir, degilse integer a cevirelim
cltv_df.dtypes
cltv_df["frequency"] = cltv_df["frequency"].astype(int)
cltv_df.dtypes

# customer_id yi yeniden index olarak atayalim
cltv_df.set_index('customer_id', inplace=True)

# degerleri kontrol edelim:
cltv_df.describe().T
cltv_df.head()

### 7) Sütun isimlerini güncelleyelim :
# (customer_id, recency_cltv_weekly, T_weekly, frequency ve monetary_cltv_avg değerlerinin yer aldığı bir cltv dataframe'i oluşturunuz.)
cltv_df.rename(columns={"T": "T_weekly", "recency": "recency_cltv_weekly", "monetary": "monetary_cltv_avg"}, inplace=True)






##############################################################
# 6. BG-NBD Modelinin Kurulması
##############################################################

# Bu model bir müşterinin beklenen satın alma sayısını tahmin etmek için kullanılır.  (Expected Total Transaction)

# Katsayılara uygulanacak ceza katsayısı: 0.001
bgf = BetaGeoFitter(penalizer_coef=0.001)

# Modeli nihai hale getir:
bgf.fit(cltv_df['frequency'],
        cltv_df['recency_cltv_weekly'],
        cltv_df['T_weekly'])


################################################################
# 1 Haftalık Satın Alma Sayısı Sonuçları
################################################################

# 1 hafta içinde en çok satın alma sayısı beklenen ilk 10 müşteri: (t:1 yani 1 haftalık tahmin yap demek)
bgf.conditional_expected_number_of_purchases_up_to_time(1,
                                                        cltv_df['frequency'],
                                                        cltv_df['recency_cltv_weekly'],
                                                        cltv_df['T_weekly']).sort_values(ascending=False).head(10)

# Veya predict fonksiyonu ile:
bgf.predict(1,
            cltv_df['frequency'],
            cltv_df['recency_cltv_weekly'],
            cltv_df['T_weekly']).sort_values(ascending=False).head(10)


# Tüm müşteriler için, 1 hafta içinde beklenen satın alma sayısı
cltv_df["expected_purc_1_week"] = bgf.predict(1,
                                              cltv_df['frequency'],
                                              cltv_df['recency_cltv_weekly'],
                                              cltv_df['T_weekly'])


################################################################
# 3 Aylık Satın Alma Sayısı Sonuçları
################################################################

# Tüm müşteriler için, 3 ay içinde beklenen satın alma sayısı
cltv_df["exp_sales_3_month"] = bgf.predict(4 * 3,
                                           cltv_df['frequency'],
                                           cltv_df['recency_cltv_weekly'],
                                           cltv_df['T_weekly']).sort_values(ascending=False)


# 3 ayda en çok satın alım gerçekleştirecek 10 müşteriyi inceleyeniz.
cltv_df.sort_values(by="exp_sales_3_month", ascending=False).head(10)


# 3 Ayda Tüm Şirketin Beklenen Satış Sayısı
bgf.predict(4 * 3,
            cltv_df['frequency'],
            cltv_df['recency_cltv_weekly'],
            cltv_df['T_weekly']).sum()


################################################################
# 6 ay içerisinde müşterilerden beklenen satın almaları tahmin ediniz ve exp_sales_6_month olarak cltv dataframe'ine ekleyiniz.
################################################################

# Tüm müşteriler icin, 24 hafta (4 hafta x 6) içinde beklenen satın alma sayısı
cltv_df["exp_sales_6_month"] = bgf.predict(4  * 6,
                                           cltv_df['frequency'],
                                           cltv_df['recency_cltv_weekly'],
                                           cltv_df['T_weekly']).sort_values(ascending=False)


# 6 ayda en çok satın alım gerçekleştirecek 10 kişiyi inceleyeniz.
cltv_df.sort_values(by="exp_sales_6_month", ascending=False).head(10)


# Tahmin Sonuçlarının Değerlendirilmesi
# Bir plot çizdirelim, actual ve model değerleri için karşılaştırma grafiği gelsin
plot_period_transactions(bgf)
plt.show()







##############################################################
# 7. GAMMA-GAMMA Modelinin Kurulması
##############################################################

# GAMMA-GAMMA modeli, bir müşterinin beklenen ortalama karini tahmin etmek için kullanılır. (Expected Average Profit)

# Katsayılara uygulanacak ceza katsayısı: 0.01
ggf = GammaGammaFitter(penalizer_coef=0.01)

# Modeli nihai hale getir:
ggf.fit(cltv_df['frequency'],
        cltv_df['monetary_cltv_avg'])


################################################################
# Müşterilerin ortalama bırakacakları değeri/kari (Expected Average Profit) tahminleyip exp_average_value olarak cltv dataframe'ine ekleyiniz.
################################################################

cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                       cltv_df['monetary_cltv_avg'])


################################################################
# Ilk 10 Müşteri icin, Expected Average Profit (beklenen kar) i getirelim
################################################################

cltv_df["expected_average_profit"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                        cltv_df['monetary_cltv_avg'])


cltv_df.sort_values(by="expected_average_profit", ascending=False).head(10)







##############################################################
# 8. BG-NBD ve GG modeli ile 6 aylık CLTV'nin hesaplanması
##############################################################

# 6 aylık CLTV hesaplayınız ve cltv ismiyle dataframe'e ekleyiniz.
# Daha önce kurduğumuz ggf modeli ve bgf modeli ile, cltv hesaplayalim  (Buradaki time aylik !)

cltv_df["cltv"] = ggf.customer_lifetime_value(bgf,
                                   cltv_df['frequency'],
                                   cltv_df['recency_cltv_weekly'],
                                   cltv_df['T_weekly'],
                                   cltv_df['monetary_cltv_avg'],
                                   time=6,    # 6 aylık !!
                                   freq="W",  # T'nin frekans bilgisi (W = haftalik)
                                   discount_rate=0.01)   # indirim yapilirsa diye indirim payi

cltv_df.head()

# index bilgisi ekleyelim, Customer ID bir index degil degisken olsun
cltv_df = cltv_df.reset_index()


## !! NOTE:
# BG-NBD nin teorisinin en kritik noktasi:
# Recency yüksek olsa da, müşteri düzenli işlem yapıyorsa, eğer churn / drop out olmamışsa, müşterinin recency si arttıkça, satın alma ihtimali yükseliyor der!!
# (Hep kullandığım bir markanın, bayadır gitmediğim mağazasına gitmeye karar vermem gibi..) (Normalde recency az ise bizim için daha iyiydi)








##############################################################
# 9. CLTV'ye Göre Segmentlerin Oluşturulması
##############################################################

# 6 aylık CLTV'ye göre, tüm müşterilerinizi 4 gruba (segmente) ayırınız ve grup isimlerini veri setine ekleyiniz.  cltv_segment ismi ile atayınız.

# Burada segmentleri otomatik belirledik, gerekirse araliklari kendimiz de ayarlayabiliriz cut fonksiyonu ile vb.
cltv_df["cltv_segment"] = pd.qcut(cltv_df["cltv"], 4, labels=["D", "C", "B", "A"])
cltv_df.sort_values(by="cltv", ascending=False).head(50)

# Segmentlerin Recency, Frequency ve Monetary ortalamalarını inceleyiniz.
cltv_df.groupby("cltv_segment").agg({"recency_cltv_weekly": ["mean"], "frequency": ["mean"], "monetary_cltv_avg": ["mean"]})



################################################################
# SONUÇ: 6 Aylık CLTV Değerleri:
################################################################

# # Tüm müşteriler için, 6 Aylık CLTV Değerleri:
cltv_df.sort_values(by="cltv", ascending=False)

# 6 Aylık CLTV Değerleri en yüksek 50 müşteriyi gözlemleyiniz.
cltv_df.sort_values(by="cltv", ascending=False).head(50)

cltv_df.loc[:, ['customer_id', 'recency_cltv_weekly', 'frequency', 'monetary_cltv_avg', 'cltv', 'cltv_segment']].sort_values(by='cltv', ascending=False).head(50)


# Ilk 50 müşteriyi incelemek icin, order_channel ve interested_in_categories_12 sutunlarini da ilk df den cagiralim
six_months_max_cltv_customers = pd.merge(cltv_df, df[["customer_id","order_channel", "interested_in_categories_12"]], how="inner", on="customer_id")
six_months_max_cltv_customers.sort_values(by="cltv", ascending=False).head(50)


six_months_max_cltv_customers.groupby("cltv_segment").agg({"exp_sales_6_month": ["sum"],
                                                           "cltv": ["sum"]})





################################################################
# Yönetime, CLTV Değerleri kapsamında kısa kısa aksiyon önerilerinde bulununuz.
################################################################

### A Segmenti (6 Ay için CLTV 1,857,360 - Beklenen Satış Adetleri 7,889):
# En yüksek CLTV değerlerine sahip bu "sadık müşterilere"; Özel Indirimler, Kişiselleştirilmiş Mail/SMS, Sadakat Programları sunarak bu müşterileri ödüllendirebilir ve gelecekteki satışlarını arttırabilirsiniz.
# Zaten satın alma adedi yüksek ve sürekli olan bu müşterilere, cross-selling ve up-selling stratejilerini uygulayarak, satın alma adetlerini ve CLTV değerlerini daha çok arttırabilirsiniz.
# Hızlı teslimat seçeneği, sınırlı sayıda ürün gibi premium hizmetler sunarak, müşteri memnuniyetini arttırabilirsiniz.
# VIP müşteri programları veya özel etkinlikler düzenleyerek, müşterilerin markaya olan ilgisini artırabilir ve satışları artırabilirsiniz.


### B Segmenti (6 Ay için CLTV 999,253 - Beklenen Satış Adetleri 6,033):
# Bu segmentteki "potansiyel sadık müşterilerin" satın alma adetlerini ve CLTV değerlerini arttırmak için cross-selling ve up-selling stratejilerini uygulayabilirsiniz. Böylece segmentin CLTV değerini arttırabilirsiniz.
# VIP müşteri programları veya özel etkinlikler düzenleyerek, müşterilerin markaya olan ilgisini artırabilir ve satışları artırabilirsiniz.


### C Segmenti (6 Ay için CLTV 690,508 - Beklenen Satış Adetleri 5,243):
# Bu segmentteki "en yüksek CLTV'ye sahip müşterilere" odaklanarak, kampanyalar ve özel indirimlerle bu müşterileri teşvik edip, segmentin CLTV değerini arttırıp, B segmentine yükselmelerini sağlayabilirsiniz.


### D Segmenti (6 Ay için CLTV 398,991 - Beklenen Satış Adetleri 4,053):
# Bu segmentteki sık alışveriş yapan müşterilere, düşük maliyetli ürünler veya hizmetler sunarak, daha sık alışveriş yapmalarını teşvik edebilir, C segmentine yükselmelerini sağlayabilirsiniz.
# Bu segmentteki müşterilerden düzenli geri bildirim alarak, ürün ve hizmetlerinizi iyileştirmek için fırsatlar arayabilirsiniz.










##############################################################
# 10. Çalışmanın Fonksiyonlaştırılması
##############################################################


def create_cltv_df(dataframe):

    # Veriyi Hazırlama
    columns = ["order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline","customer_value_total_ever_online"]
    for col in columns:
        replace_with_thresholds(dataframe, col)

    dataframe["order_num_total"] = dataframe["order_num_total_ever_online"] + dataframe["order_num_total_ever_offline"]
    dataframe["customer_value_total"] = dataframe["customer_value_total_ever_offline"] + dataframe["customer_value_total_ever_online"]
    dataframe = dataframe[~(dataframe["customer_value_total"] == 0) | (dataframe["order_num_total"] == 0)]
    date_columns = dataframe.columns[dataframe.columns.str.contains("date")]
    dataframe[date_columns] = dataframe[date_columns].apply(pd.to_datetime)

    # CLTV veri yapısının oluşturulması
    dataframe["last_order_date"].max()  # 2021-05-30
    analysis_date = dt.datetime(2021, 6, 1)
    cltv_df = pd.DataFrame()
    cltv_df["customer_id"] = dataframe["master_id"]
    cltv_df["recency_cltv_weekly"] = ((dataframe["last_order_date"] - dataframe["first_order_date"]).astype('timedelta64[D]')) / 7
    cltv_df["T_weekly"] = ((analysis_date - dataframe["first_order_date"]).astype('timedelta64[D]')) / 7
    cltv_df["frequency"] = dataframe["order_num_total"]
    cltv_df["monetary_cltv_avg"] = dataframe["customer_value_total"] / dataframe["order_num_total"]
    cltv_df = cltv_df[(cltv_df['frequency'] > 1)]

    # BG-NBD Modelinin Kurulması
    bgf = BetaGeoFitter(penalizer_coef=0.001)
    bgf.fit(cltv_df['frequency'],
            cltv_df['recency_cltv_weekly'],
            cltv_df['T_weekly'])
    cltv_df["exp_sales_3_month"] = bgf.predict(4 * 3,
                                               cltv_df['frequency'],
                                               cltv_df['recency_cltv_weekly'],
                                               cltv_df['T_weekly'])
    cltv_df["exp_sales_6_month"] = bgf.predict(4 * 6,
                                               cltv_df['frequency'],
                                               cltv_df['recency_cltv_weekly'],
                                               cltv_df['T_weekly'])

    # # Gamma-Gamma Modelinin Kurulması
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(cltv_df['frequency'], cltv_df['monetary_cltv_avg'])
    cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                           cltv_df['monetary_cltv_avg'])

    # Cltv tahmini
    cltv = ggf.customer_lifetime_value(bgf,
                                       cltv_df['frequency'],
                                       cltv_df['recency_cltv_weekly'],
                                       cltv_df['T_weekly'],
                                       cltv_df['monetary_cltv_avg'],
                                       time=6,
                                       freq="W",
                                       discount_rate=0.01)
    cltv_df["cltv"] = cltv

    # CLTV segmentleme
    cltv_df["cltv_segment"] = pd.qcut(cltv_df["cltv"], 4, labels=["D", "C", "B", "A"])

    return cltv_df

cltv_df = create_cltv_df(df)


cltv_df.head(10)


