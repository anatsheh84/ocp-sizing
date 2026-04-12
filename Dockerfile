# OCP Sizing Calculator - Container Image
# Optimized for OpenShift (runs as non-root, port 8080)

FROM python:3.12-slim

# Labels for OpenShift
LABEL io.openshift.expose-services="8080:http" \
      io.k8s.description="OCP Sizing Calculator - Kubernetes to OpenShift migration tool" \
      io.k8s.display-name="OCP Sizing Calculator" \
      maintainer="aelnatsh@redhat.com"

# Set working directory
WORKDIR /opt/app

# Ensure Python handles UTF-8 (for emoji in HTML templates)
ENV PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install Python dependencies first (layer caching)
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY models/ ./models/
COPY parsers/ ./parsers/
COPY analyzers/ ./analyzers/
COPY reporters/ ./reporters/
COPY app.py .

# OpenShift runs containers as random UID
# Ensure the app directory is readable by any user
RUN chmod -R g=u /opt/app && \
    chgrp -R 0 /opt/app

# Create temp directory writable by any user (for report generation)
RUN mkdir -p /tmp/ocp-reports && chmod 1777 /tmp/ocp-reports

EXPOSE 8080

# Run as non-root (OpenShift requirement)
USER 1001

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
