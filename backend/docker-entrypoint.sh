#!/bin/sh
set -e
# Crea las tablas y, si la base está vacía y SEED_DATOS_EJEMPLO=1, carga los datos ficticios.
if [ "${SEED_DATOS_EJEMPLO:-1}" = "1" ]; then
  python -m app.seed
else
  python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(engine)"
fi
exec "$@"
