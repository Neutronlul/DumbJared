#!/bin/sh

# Wait for the database to be ready; apply migrations if needed
until python manage.py db_isready >/dev/null 2>&1; do
  rc=$?
  
  case $rc in
    # There are migrations to apply
    1)
      echo "There are migrations to apply"
      echo "Applying now..."
      python manage.py migrate --noinput
      ;;
    # Database not ready
    2)
      echo "Waiting for database..."
      ;;
    # Unexpected error
    *)
      echo "Unexpected error; exiting with unmasked code $rc"
      exit 1
      ;;
  esac
  sleep 1
done

python manage.py check --deploy --fail-level WARNING

exec "$@"