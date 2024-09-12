### Adımlar
1. [[#Alma Linux]]
	1. [[#İndirme ve Kurulum]]
	2. [[#Firewall ve SELinux Ayarı]]
2. [[#Ön Gerekenlerin Kurulumu]]
	1. [[#Python]]
	2. [[#Postgres]]
	3. [[#Redis]]
3. [[#Netbox]] 
	1. [[#Kurulum]]
	2. [[#Deneme ve Sorun Giderme]]
	3. [[#Gunicorn Kurulumu]]
	5. [[#NGINX Kurulumu]]

## Alma Linux
--- 
### İndirme ve Kurulum
Alma Linux [sitesinden](https://almalinux.org/get-almalinux/) en son sürümü indir. Sanal veya gerçek sistem kurulumuna göre devam et ve ISO'yu bootla.

![[Pasted image 20240820151858.png]]

İlk başlayıp yüklendikten sonra bu menü ile karşılaşacaksın. Tercih edilen dil ayarını seçip devam et.

![[Pasted image 20240820152030.png]]

Bu menüde yapılması gereken adımlar:
- Yazılım Seçimi: Varsayılan seçenek arayüzlü sürümdür. Kurulum için GUI gereği olmadığından **Server** seçilebilir.
- Kurulum Hedefi: Hedef olan disk(ler)i seç.
- Kök Parolası: **Root Hesabını Kilitle**'yi seç.
- Kullanıcı Oluşturma: Kullanıcı adı ve parola girip **Yönetici Yap**'i seçin.

İsteğe göre diğer ayarlar değiştirilebilir. Sonda **Kuruluma Başla**'yı seç. Kurulum yaklaşık 10-20 dakika sürecektir. İşlem bitince **Sistemi Yeniden Başlat**'ı seç. Sunucu artık kullanıma hazırdır.

#### (Opsiyonel) SSH üzerinden bağlanma 

Sunucu açıldıktan sonra kullanıcı adı ve parolayı gir ve ``ip a`` komutunu sür.

![[Pasted image 20240820155616.png]]
Sarı ile seçilen kısım SSH için kullanılan adrestir.

### Firewall ve SELinux Ayarı

Apache ve Netbox kurulumu için sistemin güvenlik ayarlarına kural eklenmelidir:
```bash
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
setsebool -P httpd_can_network_connect 1
```

## Ön Gerekenlerin Kurulumu
---

### Python
Alma ile gelen varsayılan python versiyonu eski olduğundan daha yeni bir sürümün kurulumu gereklidir. En son stabil sürümün kurulumu tercih edilir. 20/08/2024 tarihinde bu sürüm Python 3.11 olmaktadır.

#### Adımlar

İlk olarak sistem güncellenmeli ve Python'ü yapılandırmak için gerekli programlar indirilmelidir.
```bash
sudo dnf update
sudo dnf install gcc openssl-devel bzip2-devel libffi-devel wget tar make yum-utils zlib-devel
```

Ardından Python'un kendisi indirilir ve kaynaktan kurulur.

```bash
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xf Python-3.11.9.tgz

cd Python-3.11.9
./configure --enable-optimizations
make -j ${nproc}
sudo make altinstall
```

Son olarak Python'un sorunsuz kurulduğunu doğrulamak için ``python3.11 --version`` komutunu sür. Şuna benzer bir cevap almalısın:

![[Pasted image 20240820160628.png]]

### Postgres
PostgreSQL, Netbox ile kullanılan SQL veri tabanı çözümüdür. İlk olarak Alma'yı en güncel Postgres sürümünü yüklemek için ayarlamalıyız.

```bash
# Postgres'i kur:
sudo dnf install -y postgresql-server
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
```

Ardından, ``/var/lib/pgsql/16/data/pg_hba.conf`` dosyasını açıp bu kısmı:
![[Pasted image 20240820161409.png]]

Bu şekilde değiştir:
![[Pasted image 20240820161453.png]]

Son olarak veri tabanını'i yapılandır ve başlat.
```bash
sudo systemctl enable --now postgresql
```

#### Postgres için kullanıcı tanımlama

``sudo -u postgres psql`` komutunu girip açılan shell'de aşağıdaki komutları gir:
```sql
CREATE DATABASE netbox;
CREATE USER netbox WITH PASSWORD 'beni-değiştir';
ALTER DATABASE netbox OWNER TO netbox;
\q
```
Parola kısmı için farklı bir parola seçip bir yerde sakla. Netbox kurulumu için ihtiyacın olacak.

#### Veri Tabanını Doğrula
Shell'e:
```bash
psql --username netbox --password --host localhost netbox

\conninfo
```
Komutlarını yaz. Aldığın cevap buna benzer olmalı:

![[Pasted image 20240820163415.png]]

### Redis
Redis, önbellek ve sorgu amaçlı kullanılan yardımcı bir uygulamadır. Kurulumu oldukça basittir.
```bash
sudo yum install -y redis
sudo systemctl enable --now redis
```

Ardından ``redis-cli ping`` komutu ile durumunu tespit edebilirsiniz. Cevap olarak ``PONG`` gelecektir.

## Netbox
---

### Kurulum
İlk olarak gerekli olan bütün sistem paketlerini indir:
```bash
sudo yum install -y gcc libxml2-devel libxslt-devel libffi-devel libpq-devel openssl-devel redhat-rpm-config
```

Ardından [Netbox GitHub](https://github.com/netbox-community/netbox/releases) sitesinden en son Netbox sürüm numarasını not alıp shell'den indir:
```bash
cd /opt
sudo wget https://github.com/netbox-community/netbox/archive/refs/tags/v4.0.9.tar.gz
sudo tar -xzf v4.0.9.tar.gz
sudo ln -s /opt/netbox-X.Y.Z/ /opt/netbox
```

Netbox için kullanıcı tanımla:
```bash
# Aşağıdaki iki komut sadece netbox adlı bir kullanıcı yok ise gerekli
sudo groupadd --system netbox
sudo adduser --system -g netbox netbox

sudo chown --recursive netbox /opt/netbox/netbox/media/
sudo chown --recursive netbox /opt/netbox/netbox/reports/
sudo chown --recursive netbox /opt/netbox/netbox/scripts/
```

#### Netbox'u Yapılandırma
Netbox'un ayarlamak için ilk örnek yapı dosyasının kopyasını yapmak gerek.
```bash
cd /opt/netbox/netbox/netbox/
sudo cp configuration_example.py configuration.py
```

``configuration.py`` Dosyasında değişmesi gereken üç öğe var:
- ``ALLOWED_HOSTS``
- ``DATABASE``
- ``SECRET_KEY``

``ALLOWED_HOSTS``:
```python 
ALLOWED_HOSTS = ['192.168.92.129', 'netbox.internet.world']
```
Şeklinde IP veya FQDN olabilir, veya test amaçlı
```python
ALLOWED_HOSTS = ['*']
```
şeklinde olabilir.

`DATABASE`:
```python
DATABASE = {
    'ENGINE': 'django.db.backends.postgresql',  # Database engine
    'NAME': 'netbox',         # Database name
    'USER': 'kullanıcı_adı',               # PostgreSQL username
    'PASSWORD': 'kullanıcı_parolası',           # PostgreSQL password
    'HOST': 'localhost',      # Database server
    'PORT': '',               # Database port (leave blank for default)
    'CONN_MAX_AGE': 300,      # Max database connection age
}
```

``SECRET_KEY``:
``/opt/netbox/netbox/generate_secret_key.py`` Python programı ile anahtar oluştur ve gizli anahtar kısmına gir:
```python
SECRET_KEY = 'gizli_anahtar'
```

Yukarıdaki ayarları kaydetmek ve uygulamayı güncellemek için aşağıdakini sür:
```bash
sudo PYTHON=/usr/local/bin/python3.11 /opt/netbox/upgrade.sh
```

Yeni yaratılan vENV'i aktifleştir:
```bash
source /opt/netbox/venv/bin/activate
```

Django için yeni kullanıcı yarat:
```bash
cd /opt/netbox/netbox
python3 manage.py createsuperuser
```

Temizlik ajanını aktifleştir:
```bash
sudo ln -s /opt/netbox/contrib/netbox-housekeeping.sh /etc/cron.daily/netbox-housekeeping
```

### Deneme ve Sorun Giderme

Artık Netbox, demo modunda denemek ve sorun gidermek için hazır.
```bash
python3 manage.py runserver 0.0.0.0:8000 --insecure
```
Sistemin IP adresine 8000 portundan bağlanarak panel'e erişim sağlanılabilir.

Sunucunun ulaşılamaz olması durumunda [[#Firewall ve SELinux Ayarı]] kısmındaki komutları yeniden sürmeyi dene. Alternatif olarak sunucuyu yeniden başlatıp vENV komutundan itibaren tekrar dene.

Demo sunucusunu kapatmak için klavyedeki ``Ctrl+C`` düğmelerine basın.

### Gunicorn Kurulumu

Netbox uygulaması ve Nginx Web Server'ı arasında iletişim sağlayan WSGI protokolü için Gunicorn'yi kullanacağız. uWSGI gibi diğer programlara kıyasla daha basit ve hafif olduğundan tercih edildi. 

Gunicorn'u aktive etmek için:
```bash
sudo cp /opt/netbox/contrib/gunicorn.py /opt/netbox/gunicorn.py
```

Opsiyonel olarak port ve IP'yi değiştirmek için ``/opt/netbox/gunicorn.py`` dosyasını değiştirebilirsin. Varsayılan ayar ``127.0.0.1:8001``.

Ardından uygulamayı systemd için tanımlaman gerek:
```bash
# SystemD servis sürücülerini kopyalama
sudo cp -v /opt/netbox/contrib/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Netbox sürücüsünü aktifleştirme
sudo systemctl enable --now netbox netbox-rq
```

Ardından ``systemctl status netbox.service`` komutu ile Netbox'un durumunu sorgulayabilirsin.
### NGINX Kurulumu

Aşağıdaki komutlar ile kurulumu tamamlayabilirsin:
```bash
sudo yum install -y nginx
sudo cp /opt/netbox/contrib/nginx.conf /etc/nginx/conf.d/netbox.conf

sudo systemctl restart nginx
```

Bu noktada Netbox, kendiliğinden çalışır ve sunucu açılışında aktif halde olacaktır.
