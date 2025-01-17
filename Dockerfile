FROM selenium/standalone-chrome-debug

USER root

RUN apt-get update && apt-get upgrade -y

RUN apt-get update && apt-get install -y \
	build-essential python-dev python-setuptools python3-pip python3-smbus \
	libncursesw5-dev libgdbm-dev libc6-dev \
	zlib1g-dev libsqlite3-dev tk-dev \
	libssl-dev \
	libffi-dev

RUN cd /opt/ && wget https://www.python.org/ftp/python/3.7.1/Python-3.7.1.tgz
RUN cd /opt/ && tar -xzf Python-3.7.1.tgz
RUN cd /opt/Python-3.7.1 && ./configure
RUN cd /opt/Python-3.7.1 && make
RUN cd /opt/Python-3.7.1 && make install

#Upgrading pip resolves error with MarkupSafe
RUN pip3 install -U pip setuptools wheel
RUN pip3 install -U selenium mitmproxy paho-mqtt asyncio
RUN pip3 install markupsafe==2.0.1
ADD ./docker/entry_point.sh /opt/bin/entry_point.sh
RUN sed -i -e 's/\r$//' /opt/bin/entry_point.sh
RUN chmod +x /opt/bin/entry_point.sh
ADD ./docker/run.sh /opt/run.sh
RUN sed -i -e 's/\r$//' /opt/run.sh
RUN chmod +x /opt/run.sh
ADD ./python/smartrent-bridge.py /opt/smartrent-bridge.py
ADD ./python/smartrent-login.py /opt/smartrent-login.py
ADD ./python/health-check.py /opt/health-check.py

HEALTHCHECK --interval=60s --timeout=5s --start-period=120s CMD python3 /opt/health-check.py