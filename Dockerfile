FROM rockylinux:9-minimal

# LABEL info from: https://github.com/opencontainers/image-spec/blob/main/annotations.md

LABEL org.opencontainers.image.authors=secure.software@reversinglabs.com
LABEL org.opencontainers.image.url=https://www.secure.software/
LABEL org.opencontainers.image.vendor=ReversingLabs

RUN microdnf install -y --nodocs python3-pip && pip3 install --no-cache-dir rl-deploy && microdnf clean all
COPY scripts/* /opt/rl-scanner/
RUN chmod 755 /opt/rl-scanner/entrypoint /opt/rl-scanner/rl-scan /opt/rl-scanner/rl-prune
ENV PATH="/opt/rl-scanner:${PATH}"

ENTRYPOINT [ "/opt/rl-scanner/entrypoint" ]
