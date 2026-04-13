# OpenShift Assessment Tools - Container Image
# Unified: OCP Sizing Calculator + VM Migration Assessment
# Optimized for OpenShift (runs as non-root, port 8080)

FROM python:3.12-slim

# Labels for OpenShift
LABEL io.openshift.expose-services="8080:http" \
      io.k8s.description="OpenShift Assessment Tools - Sizing and Migration" \
      io.k8s.display-name="OpenShift Assessment Tools" \
      maintainer="aelnatsh@redhat.com"

WORKDIR /opt/app

# Ensure Python handles UTF-8 (for emoji in HTML templates)
ENV PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install Python dependencies first (layer caching)
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy OCP Sizing modules
COPY models/ ./models/
COPY parsers/ ./parsers/
COPY analyzers/ ./analyzers/
COPY reporters/ ./reporters/

# Copy VM Migration modules
COPY sources/ ./sources/
COPY components/ ./components/
COPY data_processor.py .
COPY generate_dashboard.py .

# Copy unified web app
COPY app.py .

# OpenShift runs containers as random UID
RUN chmod -R g=u /opt/app && \
    chgrp -R 0 /opt/app

# Create temp directory writable by any user
RUN mkdir -p /tmp/ocp-reports && chmod 1777 /tmp/ocp-reports

EXPOSE 8080

USER 1001

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
