# Use the official Prometheus image
FROM prom/prometheus:v2.45.0

# Create directories and set permissions as root
USER root
RUN mkdir -p /prometheus /etc/prometheus/rules && \
    chown -R nobody:nobody /prometheus /etc/prometheus

# Copy configuration files
COPY monitoring/prometheus/prometheus.yml /etc/prometheus/
COPY monitoring/prometheus/rules/ /etc/prometheus/rules/

# Verify configuration
RUN promtool check config /etc/prometheus/prometheus.yml

# Switch back to nobody user
USER nobody

# Expose Prometheus web interface port
EXPOSE 9090

# Define volumes for persistence
VOLUME [ "/prometheus" ]

# Command to run Prometheus with configuration
CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles", \
     "--web.enable-lifecycle"]