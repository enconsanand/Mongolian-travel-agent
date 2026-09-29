#!/usr/bin/env bash
# Usage: MONGO_URI="mongodb+srv://user:pass@cluster/travel" ./import.sh
# Plain fallback import, e.g. into Atlas without Docker: replaces the collections, no validators.
# Indexes are created by the backend when it starts (app/db/mongo.py). Login users are NOT imported
# here (they need a password hash): run `make seed` for those. Prefer `make seed` in general.
set -euo pipefail
URI="${MONGO_URI:-mongodb://localhost:27017/travel_mn}"
cd "$(dirname "$0")"
for f in regions places routes events stays cancellation_policies stay_availability drivers vehicles \
         vehicle_availability transport_schedules transport_availability shared_rides trips itinerary_versions \
         quotes bookings payments refunds app_config audit_log conversations agent_state user_memory; do
  mongoimport --uri "$URI" --collection "$f" --file "$f.json" --jsonArray --drop
done
echo "Imported. Start the backend once to create the indexes."
