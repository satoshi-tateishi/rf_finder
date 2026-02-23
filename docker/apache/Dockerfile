FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    apache2 \
    libapache2-mod-auth-mellon \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN a2enmod proxy proxy_http rewrite ssl headers auth_mellon

COPY docker/apache/vhost.conf /etc/apache2/sites-available/000-default.conf

# Define standard log locations
ENV APACHE_LOG_DIR /var/log/apache2

EXPOSE 80 443

CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
