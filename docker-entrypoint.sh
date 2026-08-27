#!/bin/sh
set -eu

secret_source=/run/secrets/line_works_private_key
secret_dir=/run/rf_finder
secret_target=${secret_dir}/line_works_private_key

if [ -f "${secret_source}" ]; then
    install -d -m 0700 -o appuser -g appgroup "${secret_dir}"
    install -m 0400 -o appuser -g appgroup "${secret_source}" "${secret_target}"
fi

exec setpriv --reuid=appuser --regid=appgroup --init-groups "$@"
