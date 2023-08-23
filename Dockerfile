FROM python:bookworm

COPY . /app
WORKDIR /app
RUN useradd -s /bin/bash -m app && \
    chown -R app:app . && \
    gcc ./readflag.c -o /readflag && \
    chmod u+s /readflag 

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install . && \
    cd ./checkpoints && \
    wget https://github.com/AUTOMATIC1111/TorchDeepDanbooru/releases/download/v1/model-resnet_custom_v3.pt && \
    pip cache purge

EXPOSE 8080
ENV HOST=0.0.0.0 \ 
    PORT=8080

CMD ["/bin/bash","-c","\
    echo -n $FLAG > /flag && \
    unset FLAG && \
    chmod 700 /flag && \
    su app -c 'python -m vulnbooru'"]
