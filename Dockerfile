# Python 3.9.18 / Debian 11 snapshot. Intentionally old; findings must be confirmed.
FROM python:3.9.18-bullseye@sha256:4f998c9362c1dc3e72f0b758c63e60896bf8dbc1e57f851c15d0eaa1cb1083ca
# 1,152 MiB deterministic, non-sensitive padding; highly compressible by design.
RUN python -c "import os; p='/opt/metlife-benchmark-data'; block=(b'MetLife benchmark fixture. '*65536)[:1048576]; f=open(p,'wb'); [f.write(block) for _ in range(1152)]; f.close(); os.utime(p,(0,0))"
CMD ["python", "--version"]
